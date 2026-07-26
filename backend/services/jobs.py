"""
Generation job registry.

The previous implementation was a bare module-level ``dict`` mutated from
background tasks. That had three problems:

1. **Unbounded growth.** Jobs (and the ZIP/PNG files they reference) were never
   removed, so a long-running server leaked disk and memory indefinitely.
2. **No synchronisation.** Jobs were mutated from worker threads while request
   handlers read them. Dict operations are individually atomic under the GIL,
   but a read-modify-write like ``job["progress"] += 1`` is not.
3. **Untyped payload.** Every call site guessed at the shape of the dict, and a
   typo in a key silently produced ``None``.

This module replaces it with a typed, lock-guarded store with TTL cleanup.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from core.logging_config import get_logger

logger = get_logger(__name__)


class JobStatus(StrEnum):
    """Lifecycle states of a generation job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


@dataclass
class GenerationJob:
    """State of a single map generation."""

    job_id: str
    map_name: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    #: Files produced by this job, keyed by role ("archive", "preview", ...).
    #: Tracked explicitly so downloads never rebuild a path from user input and
    #: so cleanup knows exactly what to delete.
    artifacts: dict[str, Path] = field(default_factory=dict)

    #: Free-form extras surfaced to the UI (feature counts, source name, ...).
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the HTTP API."""
        payload: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "map_name": self.map_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.stats:
            payload["stats"] = self.stats
        if self.status is JobStatus.COMPLETED:
            if "archive" in self.artifacts:
                payload["download_url"] = f"/api/download/{self.job_id}"
            if "preview" in self.artifacts:
                payload["preview_url"] = f"/api/preview/{self.job_id}"
        return payload


class JobStore:
    """Thread-safe in-memory job registry with TTL-based cleanup."""

    def __init__(self, retention_seconds: int = 24 * 60 * 60) -> None:
        self._jobs: dict[str, GenerationJob] = {}
        self._lock = threading.RLock()
        self.retention_seconds = retention_seconds

    def create(self, map_name: str) -> GenerationJob:
        """Register a new job and return it."""
        job = GenerationJob(job_id=str(uuid.uuid4()), map_name=map_name)
        with self._lock:
            self._jobs[job.job_id] = job
        logger.info("Job %s created for map %r", job.job_id, map_name)
        return job

    def get(self, job_id: str) -> GenerationJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> GenerationJob | None:
        """
        Apply a partial update to a job.

        Returns the updated job, or ``None`` if it no longer exists (it may
        have been cleaned up while a long generation was running).
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            if status is not None:
                job.status = status
                if status.is_terminal:
                    job.finished_at = time.time()
            if progress is not None:
                job.progress = max(0, min(100, progress))
            if message is not None:
                job.message = message
            if error is not None:
                job.error = error
            if stats:
                job.stats.update(stats)

            job.updated_at = time.time()
            return job

    def attach_artifact(self, job_id: str, role: str, path: Path) -> None:
        """Record a file produced by the job so it can be served and cleaned up."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.artifacts[role] = Path(path)

    def get_artifact(self, job_id: str, role: str) -> Path | None:
        """Return a job artefact path, or ``None`` if absent."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return job.artifacts.get(role)

    def active_count(self) -> int:
        """Number of jobs that have not reached a terminal state."""
        with self._lock:
            return sum(1 for job in self._jobs.values() if not job.status.is_terminal)

    def __len__(self) -> int:
        with self._lock:
            return len(self._jobs)

    def __iter__(self) -> Iterator[GenerationJob]:
        with self._lock:
            return iter(list(self._jobs.values()))

    def cleanup_expired(self, *, now: float | None = None, delete_files: bool = True) -> int:
        """
        Remove finished jobs older than the retention window.

        Args:
            now: Override the current time (used by tests).
            delete_files: Also unlink the artefacts the job produced.

        Returns:
            Number of jobs removed.
        """
        current = time.time() if now is None else now
        removed: list[GenerationJob] = []

        with self._lock:
            for job_id, job in list(self._jobs.items()):
                if not job.status.is_terminal:
                    continue
                reference = job.finished_at or job.updated_at
                if current - reference >= self.retention_seconds:
                    removed.append(self._jobs.pop(job_id))

        if delete_files:
            for job in removed:
                for role, path in job.artifacts.items():
                    try:
                        Path(path).unlink(missing_ok=True)
                    except OSError as exc:  # pragma: no cover - platform dependent
                        logger.warning("Could not delete %s artefact %s: %s", role, path, exc)

        if removed:
            logger.info("Cleaned up %d expired job(s)", len(removed))
        return len(removed)

    def clear(self) -> None:
        """Drop every job (tests only)."""
        with self._lock:
            self._jobs.clear()


#: Process-wide job registry. Replaced wholesale in tests.
job_store = JobStore()

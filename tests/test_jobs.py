"""Job registry: state transitions, artefact tracking, TTL cleanup, thread safety."""

from __future__ import annotations

import threading
import time

from services.jobs import GenerationJob, JobStatus, JobStore


def test_create_returns_unique_queued_jobs(job_store):
    first = job_store.create("map_one")
    second = job_store.create("map_two")

    assert first.job_id != second.job_id
    assert first.status is JobStatus.QUEUED
    assert len(job_store) == 2


def test_update_clamps_progress(job_store):
    job = job_store.create("m")

    assert job_store.update(job.job_id, progress=150).progress == 100
    assert job_store.update(job.job_id, progress=-20).progress == 0


def test_update_of_missing_job_returns_none(job_store):
    assert job_store.update("does-not-exist", progress=10) is None


def test_terminal_status_records_finish_time(job_store):
    job = job_store.create("m")
    assert job.finished_at is None

    updated = job_store.update(job.job_id, status=JobStatus.COMPLETED)
    assert updated.finished_at is not None


def test_to_dict_exposes_urls_only_when_complete(job_store, tmp_path):
    job = job_store.create("m")
    archive = tmp_path / "m.zip"
    archive.write_bytes(b"zip")
    job_store.attach_artifact(job.job_id, "archive", archive)

    assert "download_url" not in job_store.get(job.job_id).to_dict()

    job_store.update(job.job_id, status=JobStatus.COMPLETED)
    payload = job_store.get(job.job_id).to_dict()
    assert payload["download_url"] == f"/api/download/{job.job_id}"


def test_cleanup_removes_expired_jobs_and_their_files(tmp_path):
    store = JobStore(retention_seconds=60)
    job = store.create("old_map")

    archive = tmp_path / "old_map.zip"
    archive.write_bytes(b"data")
    store.attach_artifact(job.job_id, "archive", archive)
    store.update(job.job_id, status=JobStatus.COMPLETED)

    # Not yet expired.
    assert store.cleanup_expired() == 0
    assert archive.exists()

    assert store.cleanup_expired(now=time.time() + 120) == 1
    assert not archive.exists()
    assert store.get(job.job_id) is None


def test_cleanup_never_removes_running_jobs(job_store):
    job = job_store.create("running")
    job_store.update(job.job_id, status=JobStatus.PROCESSING)

    assert job_store.cleanup_expired(now=time.time() + 10_000) == 0
    assert job_store.get(job.job_id) is not None


def test_active_count_tracks_non_terminal_jobs(job_store):
    running = job_store.create("a")
    done = job_store.create("b")
    job_store.update(done.job_id, status=JobStatus.COMPLETED)

    assert job_store.active_count() == 1
    job_store.update(running.job_id, status=JobStatus.FAILED)
    assert job_store.active_count() == 0


def test_concurrent_updates_do_not_lose_writes(job_store):
    """
    The old store was a bare dict mutated from background threads.

    Each thread here writes a distinct stats key; with unsynchronised
    read-modify-write on a shared dict some of them can be lost.
    """
    job = job_store.create("concurrent")
    thread_count = 24
    barrier = threading.Barrier(thread_count)

    def worker(index: int) -> None:
        barrier.wait()
        job_store.update(job.job_id, stats={f"key_{index}": index})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(job_store.get(job.job_id).stats) == thread_count


def test_job_status_terminality():
    assert JobStatus.COMPLETED.is_terminal
    assert JobStatus.FAILED.is_terminal
    assert JobStatus.CANCELLED.is_terminal
    assert not JobStatus.QUEUED.is_terminal
    assert not JobStatus.PROCESSING.is_terminal


def test_generation_job_serialises_stats():
    job = GenerationJob(job_id="abc", map_name="m", stats={"roads": 3})
    assert job.to_dict()["stats"] == {"roads": 3}

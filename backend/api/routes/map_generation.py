"""Map generation API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from core.logging_config import get_logger
from models.map_request import (
    JobStatusResponse,
    MapGenerationRequest,
    MapGenerationResponse,
)
from services.data_sources import DataSourceFactory, DataSourceType
from services.data_sources.base import Capability
from services.jobs import JobStatus, job_store
from services.pipeline import MapGenerationPipeline

logger = get_logger(__name__)

router = APIRouter()

#: One pipeline per process; it owns the concurrency semaphore.
_pipeline: MapGenerationPipeline | None = None


def get_pipeline() -> MapGenerationPipeline:
    """Return the shared pipeline, constructing it on first use."""
    global _pipeline
    if _pipeline is None:
        _pipeline = MapGenerationPipeline(job_store=job_store)
    return _pipeline


@router.get("/data-sources")
async def get_data_sources() -> dict:
    """
    List data sources with their availability.

    Never fails as a whole: a provider that raises while being probed is
    reported as unavailable with the reason attached, so one broken integration
    cannot blank out the entire picker.
    """
    sources = []
    for source_type in DataSourceType:
        try:
            source = DataSourceFactory.create(source_type)
            sources.append(
                {
                    "id": source_type.value,
                    "name": source.get_source_name(),
                    "description": source.get_source_description(),
                    "available": source.is_available(),
                    "requires_setup": source.requires_setup(),
                    "provides": sorted(capability.value for capability in source.capabilities),
                    "recommended": source_type is DataSourceType.OPENTOPOGRAPHY,
                    "deprecated": source_type is DataSourceType.BING_MAPS,
                }
            )
        except Exception as exc:  # noqa: BLE001 - one bad source must not break the list
            logger.warning("Could not probe %s: %s", source_type.value, exc)
            sources.append(
                {
                    "id": source_type.value,
                    "name": source_type.value,
                    "description": f"Unavailable: {exc}",
                    "available": False,
                    "requires_setup": True,
                    "provides": [],
                    "recommended": False,
                    "deprecated": False,
                }
            )

    default_source = DataSourceFactory.first_available(
        tuple(DataSourceType), Capability.DEM
    )

    return {
        "sources": sources,
        "default": next(
            (
                source["id"]
                for source in sources
                if default_source and source["name"] == default_source.get_source_name()
            ),
            None,
        ),
        "message": "Use 'auto' to let the server pick the best configured source.",
    }


@router.post("/generate", response_model=MapGenerationResponse, status_code=202)
async def generate_map(
    request: MapGenerationRequest, background_tasks: BackgroundTasks
) -> MapGenerationResponse:
    """
    Start map generation.

    Returns immediately with a job id; poll ``/api/status/{job_id}`` for
    progress. The request body is fully validated first (name slug, bbox
    extent, power-of-two heightmap), so an invalid request fails with a 422 and
    a clear message rather than halfway through the pipeline.
    """
    job = job_store.create(request.name)

    logger.info(
        "Job %s queued: %s, bbox=%s, %.2f km2, source=%s",
        job.job_id,
        request.name,
        request.bbox.to_list(),
        request.bbox.area_km2,
        request.data_source,
    )

    # A *sync* callable, so Starlette runs it in the worker thread pool instead
    # of on the event loop.
    background_tasks.add_task(get_pipeline().run, job.job_id, request)

    return MapGenerationResponse(
        success=True,
        message="Map generation started",
        map_id=job.job_id,
        map_name=job.map_name,
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(job_id: str) -> JobStatusResponse:
    """Get the status of a generation job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return JobStatusResponse(**job.to_dict())


@router.get("/jobs")
async def list_jobs() -> dict:
    """List known jobs, newest first."""
    jobs = sorted(job_store, key=lambda job: job.created_at, reverse=True)
    return {"jobs": [job.to_dict() for job in jobs], "count": len(jobs)}


@router.get("/download/{job_id}")
async def download_map(job_id: str) -> FileResponse:
    """
    Download the generated mod archive.

    The file path comes from the job's recorded artefacts, never from
    user-controlled input. The previous implementation rebuilt it as
    ``output / f"{job['map_name']}.zip"``, which let a crafted map name reach
    any file the server process could read.
    """
    return _serve_artifact(job_id, "archive", media_type="application/zip", as_attachment=True)


@router.get("/preview/{job_id}")
async def get_preview(job_id: str) -> FileResponse:
    """Get the rendered heightmap preview image."""
    return _serve_artifact(job_id, "preview", media_type="image/png", as_attachment=False)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> dict:
    """Delete a job and the files it produced."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.status.is_terminal:
        raise HTTPException(status_code=409, detail="Job is still running")

    for path in job.artifacts.values():
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - platform dependent
            logger.warning("Could not delete %s: %s", path, exc)

    job_store.update(job_id, status=JobStatus.CANCELLED)
    job_store.cleanup_expired(now=job.updated_at + job_store.retention_seconds + 1)
    return {"deleted": job_id}


def _serve_artifact(
    job_id: str, role: str, *, media_type: str, as_attachment: bool
) -> FileResponse:
    """Resolve and serve a job artefact, with precise error codes."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if job.status is JobStatus.FAILED:
        raise HTTPException(status_code=409, detail=job.error or "Map generation failed")
    if job.status is not JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Map generation is not finished yet ({job.progress}%)",
        )

    path = job.artifacts.get(role)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"{role.title()} file is no longer available")

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=f"{job.map_name}.zip" if as_attachment else None,
    )

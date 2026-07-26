"""
BeamNG.WorldForge - backend API server.

FastAPI application that turns a selected map region into a BeamNG.drive mod.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import map_generation
from api.routes import settings as settings_routes
from core.config import get_settings
from core.logging_config import configure_logging, get_logger
from services.jobs import job_store

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

APP_VERSION = "1.6.1"

#: How often finished jobs are swept.
_CLEANUP_INTERVAL_SECONDS = 15 * 60


async def _cleanup_loop() -> None:
    """
    Periodically drop expired jobs and their files.

    Without this the in-memory job registry and the ``output``/``temp``
    directories grew without bound for the lifetime of the process.
    """
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(job_store.cleanup_expired)
        except Exception:  # noqa: BLE001 - a failed sweep must not kill the task
            logger.exception("Job cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting BeamNG.WorldForge %s", APP_VERSION)

    settings.ensure_directories()
    job_store.retention_seconds = settings.job_retention_seconds
    logger.info("Output: %s | Temp: %s | Config: %s",
                settings.output_dir, settings.temp_dir, settings.config_dir)

    cleanup_task = asyncio.create_task(_cleanup_loop())

    yield

    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    logger.info("Shutting down BeamNG.WorldForge")


app = FastAPI(
    title="BeamNG.WorldForge API",
    description="Generate BeamNG.drive maps from real elevation and satellite data",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Return validation errors in a shape the UI can display.

    FastAPI's default payload nests the message inside a list of dicts, which
    the frontend rendered as ``[object Object]``. Flattening it here means a
    bad map name or an oversized region shows the actual reason.
    """
    messages = []
    fields = []
    for error in exc.errors():
        location = " -> ".join(str(part) for part in error["loc"] if part != "body")
        messages.append(f"{location}: {error['msg']}" if location else error["msg"])
        # Only the JSON-safe parts: pydantic puts the original exception object
        # in `ctx`, which the default JSON encoder cannot serialise and which
        # would turn a 422 into a 500.
        fields.append({"field": location, "message": error["msg"], "type": error["type"]})

    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(messages), "errors": fields},
    )


# -- API routes -----------------------------------------------------------------
# Registered before the SPA fallback below. Order matters: FastAPI matches
# routes in registration order, and the catch-all "/{full_path:path}" would
# otherwise shadow every API path declared after it - which is exactly what
# happened to /api/health, making it return 404 in the bundled build.

app.include_router(map_generation.router, prefix="/api", tags=["map-generation"])
app.include_router(settings_routes.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    """Health check with a snapshot of server state."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "jobs": {"total": len(job_store), "active": job_store.active_count()},
        "frontend_bundled": settings.bundled_static_dir.exists(),
    }


# -- Frontend -------------------------------------------------------------------

_static_dir = settings.bundled_static_dir

if (_static_dir / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")


@app.get("/", include_in_schema=False, response_model=None)
async def serve_index() -> FileResponse | dict:
    """Serve the SPA entry point, or API metadata when no frontend is bundled."""
    index = _static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "name": "BeamNG.WorldForge API",
        "version": APP_VERSION,
        "status": "running",
        "mode": "API-only (no frontend bundled)",
        "docs": "/docs",
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str) -> FileResponse:
    """
    Serve static files, falling back to index.html for client-side routes.

    Any unmatched ``/api/`` path is a genuine 404 rather than the SPA shell:
    returning HTML from an API path makes the frontend's JSON parsing fail with
    an unhelpful error.
    """
    if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
        raise HTTPException(status_code=404, detail="Not found")

    index = _static_dir / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend is not bundled with this build")

    # Resolve requested files under the static dir only; a request for
    # "../../config/settings.key" must not escape it.
    try:
        candidate = (_static_dir / full_path).resolve()
        if candidate.is_file() and _static_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
    except (OSError, ValueError):
        pass

    return FileResponse(index)


def main() -> None:
    """Run the server, opening a browser when launched as a bundled executable."""
    is_bundled = getattr(sys, "frozen", False)

    if is_bundled:
        import webbrowser
        from threading import Timer

        url = f"http://127.0.0.1:{settings.api_port}"
        Timer(2.0, lambda: webbrowser.open(url)).start()
        logger.info("BeamNG.WorldForge %s starting on %s", APP_VERSION, url)

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

"""
Map generation pipeline.

Previously this lived inline in the API route as one 200-line function that
mixed HTTP concerns, orchestration, progress reporting and error handling. It
is extracted here so it can be unit-tested without an HTTP client, and so the
route is just request validation plus job bookkeeping.

Two structural problems are fixed along the way:

**The pipeline no longer blocks the event loop.** ``run_map_generation`` was
declared ``async`` but its body was entirely synchronous and CPU/network bound
(``requests.get``, ``scipy.ndimage.zoom``, PNG encoding). Registered as a
FastAPI background task, it therefore ran *on the event loop*, freezing every
other request - including the status polling the UI depends on - for the whole
generation. :meth:`MapGenerationPipeline.run` is a plain sync function, which
FastAPI dispatches to its worker thread pool.

**Progress is declared, not hand-computed.** Stage weights live in one table,
so the reported percentage always matches the stages actually executed.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from core.config import Settings, get_settings
from core.geo import bbox_dimensions
from core.logging_config import get_logger
from core.paths import safe_join
from core.projection import LocalProjection, TerrainSampler
from models.map_request import MapGenerationRequest
from models.terrain import HeightmapConfig, TerrainData
from services.data_sources import DataSourceFactory, DataSourceType
from services.data_sources.base import Capability, DataSourceInterface
from services.data_sources.factory import NoDataSourceAvailableError
from services.export.beamng_exporter import BeamNGExporter
from services.jobs import JobStatus, JobStore
from services.terrain.processor import TerrainProcessor

logger = get_logger(__name__)


class PipelineError(RuntimeError):
    """Raised when a generation stage fails in a way the user can act on."""


#: Exceptions that always indicate a defect in this code rather than a missing
#: optional dependency or an unreachable service. They must never be absorbed
#: by a degrade-gracefully handler.
_PROGRAMMING_ERRORS = (NameError, AttributeError, TypeError, ImportError, IndexError, KeyError)


@dataclass
class LevelContent:
    """Placeable content derived from detected vectors."""

    decal_roads: dict | None = None
    building_items: list[dict] = field(default_factory=list)
    mesh_files: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage:
    """One step of the pipeline, with the share of total progress it covers."""

    key: str
    label: str
    weight: int


#: Base stages, always executed.
BASE_STAGES: tuple[Stage, ...] = (
    Stage("validate", "Validating request", 5),
    Stage("fetch_dem", "Downloading elevation data", 30),
    Stage("process_terrain", "Processing terrain", 20),
    Stage("heightmap", "Generating heightmap", 20),
    Stage("preview", "Rendering preview", 10),
    Stage("package", "Packaging BeamNG mod", 15),
)

#: Extra stages inserted when AI segmentation is enabled.
AI_STAGES: tuple[Stage, ...] = (
    Stage("fetch_imagery", "Downloading satellite imagery", 15),
    Stage("segment", "Detecting features with AI", 20),
    Stage("vectorize", "Extracting vector geometry", 10),
)


class ProgressReporter:
    """
    Translates stage completion into a 0-100 progress value.

    Keeping the arithmetic here means adding a stage cannot desynchronise the
    progress bar from reality, which is what happened when each call site
    hardcoded its own percentage.
    """

    def __init__(self, stages: tuple[Stage, ...], on_update: Callable[[int, str], None]) -> None:
        self._stages = stages
        self._on_update = on_update
        self._total_weight = sum(stage.weight for stage in stages) or 1
        self._completed_weight = 0

    def start(self, key: str) -> None:
        """Report that a stage has begun."""
        stage = self._stage(key)
        percent = int(self._completed_weight / self._total_weight * 100)
        self._on_update(percent, stage.label)

    def finish(self, key: str, message: str | None = None) -> None:
        """Report that a stage is complete."""
        stage = self._stage(key)
        self._completed_weight += stage.weight
        percent = int(self._completed_weight / self._total_weight * 100)
        self._on_update(min(percent, 99), message or f"{stage.label} - done")

    def _stage(self, key: str) -> Stage:
        for stage in self._stages:
            if stage.key == key:
                return stage
        raise KeyError(f"Unknown pipeline stage: {key}")


class MapGenerationPipeline:
    """Runs a map generation request end to end."""

    def __init__(
        self,
        job_store: JobStore,
        settings: Settings | None = None,
        *,
        terrain_processor: TerrainProcessor | None = None,
    ) -> None:
        self.job_store = job_store
        self.settings = settings or get_settings()
        self.terrain = terrain_processor or TerrainProcessor()

        # Bounds how many generations run at once. Each holds a full DEM plus
        # its resampled heightmap in memory, so unbounded concurrency is a
        # straightforward way to OOM the server.
        self._slots = threading.Semaphore(self.settings.max_concurrent_jobs)

    # -- entry point ----------------------------------------------------------

    def run(self, job_id: str, request: MapGenerationRequest) -> None:
        """
        Execute the pipeline for ``job_id``.

        Synchronous by design: FastAPI runs sync background tasks in a worker
        thread, which keeps the event loop free to answer status polls.
        Never raises - failures are recorded on the job.
        """
        acquired = self._slots.acquire(timeout=self.settings.http_timeout_seconds)
        if not acquired:
            self._fail(job_id, "Server is busy with other generations. Try again shortly.")
            return

        try:
            self._run_stages(job_id, request)
        except PipelineError as exc:
            logger.warning("Job %s failed: %s", job_id, exc)
            self._fail(job_id, str(exc))
        except Exception as exc:  # noqa: BLE001 - background task must not die silently
            logger.exception("Job %s failed unexpectedly", job_id)
            self._fail(job_id, f"Unexpected error: {exc}")
        finally:
            self._slots.release()

    # -- stages ---------------------------------------------------------------

    def _run_stages(self, job_id: str, request: MapGenerationRequest) -> None:
        stages = BASE_STAGES
        if request.use_ai_segmentation:
            # Imagery stages run between DEM download and terrain processing.
            stages = BASE_STAGES[:2] + AI_STAGES + BASE_STAGES[2:]

        progress = ProgressReporter(
            stages,
            lambda percent, message: self.job_store.update(
                job_id, status=JobStatus.PROCESSING, progress=percent, message=message
            ),
        )

        work_dir = safe_join(self.settings.temp_dir, request.name)
        work_dir.mkdir(parents=True, exist_ok=True)

        # -- validate ---------------------------------------------------------
        progress.start("validate")
        source = self._resolve_dem_source(request.data_source)
        self.job_store.update(job_id, stats={"data_source": source.get_source_name()})
        progress.finish("validate", f"Using {source.get_source_name()}")

        # -- DEM --------------------------------------------------------------
        progress.start("fetch_dem")
        bbox = request.bbox.to_list()
        try:
            dem_data, dem_metadata = source.get_dem_data(bbox=bbox, resolution=request.resolution)
        except NotImplementedError as exc:
            raise PipelineError(
                f"{source.get_source_name()} does not provide elevation data. "
                f"Choose a different data source."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
            raise PipelineError(f"Could not download elevation data: {exc}") from exc
        progress.finish("fetch_dem", f"Elevation data downloaded ({dem_data.shape[1]}x{dem_data.shape[0]})")

        # -- optional AI ------------------------------------------------------
        vector_data: dict[str, list] | None = None
        if request.use_ai_segmentation:
            vector_data = self._run_ai_stages(job_id, request, bbox, work_dir, progress)

        # -- terrain ----------------------------------------------------------
        progress.start("process_terrain")
        terrain = self.terrain.process_dem(dem_data)
        # BeamNG terrain blocks are square. Crop before resampling so the
        # exported map is not stretched along its shorter axis.
        terrain, effective_bbox = self.terrain.crop_to_square(terrain, bbox)
        self.job_store.update(job_id, stats={"terrain": terrain.summary()})
        progress.finish("process_terrain")

        # -- heightmap --------------------------------------------------------
        progress.start("heightmap")
        heightmap = self.terrain.generate_heightmap(
            terrain,
            HeightmapConfig(size=request.heightmap_size, bit_depth=16),
        )
        heightmap_path = self.terrain.save_heightmap(
            heightmap, work_dir / "heightmap.png", bit_depth=16
        )
        progress.finish("heightmap")

        # -- preview ----------------------------------------------------------
        progress.start("preview")
        preview_path = self.terrain.generate_preview(heightmap, work_dir / "preview.png")
        self.job_store.attach_artifact(job_id, "preview", preview_path)
        progress.finish("preview")

        # -- level content ----------------------------------------------------
        # Detected roads and buildings only become level content once the
        # heightmap exists: their heights are sampled from it, so they sit on
        # the terrain instead of floating at sea level.
        level_content = self._build_level_content(
            vector_data, effective_bbox, heightmap, terrain, work_dir
        )
        if level_content.stats:
            self.job_store.update(job_id, stats=level_content.stats)

        # -- package ----------------------------------------------------------
        progress.start("package")
        exporter = BeamNGExporter(output_dir=self.settings.output_dir)
        archive_path = exporter.create_map_structure(
            map_name=request.name,
            heightmap_path=heightmap_path,
            preview_path=preview_path,
            terrain=terrain,
            bbox=effective_bbox,
            source_name=source.get_source_name(),
            vector_data=vector_data,
            decal_roads=level_content.decal_roads,
            building_items=level_content.building_items,
            mesh_files=level_content.mesh_files,
        )
        self.job_store.attach_artifact(job_id, "archive", archive_path)
        progress.finish("package")

        size_mb = archive_path.stat().st_size / (1024 * 1024)
        self.job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message=f"Done - {archive_path.name} ({size_mb:.1f} MB)",
            stats={
                "archive_size_mb": round(size_mb, 2),
                "dem_resolution_m": dem_metadata.get("resolution", request.resolution),
            },
        )
        logger.info("Job %s completed: %s (%.1f MB)", job_id, archive_path, size_mb)

    # -- level content --------------------------------------------------------

    def _build_level_content(
        self,
        vector_data: dict[str, list] | None,
        bbox: list[float],
        heightmap: np.ndarray,
        terrain: TerrainData,
        work_dir: Path,
    ) -> LevelContent:
        """
        Turn detected vectors into placeable BeamNG level content.

        Returns empty content when nothing was detected, which is the normal
        case: AI segmentation is off by default.
        """
        if not vector_data:
            return LevelContent()

        roads = vector_data.get("roads") or []
        buildings = vector_data.get("buildings") or []
        if not roads and not buildings:
            return LevelContent()

        from services.beamng_integration import BuildingPlacer, MeshBuilder, RoadBuilder

        projection = LocalProjection.from_bbox(bbox)
        square_size = bbox_dimensions(*bbox).max_side_meters / heightmap.shape[0]
        sampler = TerrainSampler(
            heightmap,
            min_elevation=terrain.min_elevation,
            elevation_range=terrain.elevation_range,
            square_size=square_size,
        )

        content = LevelContent()

        if roads:
            content.decal_roads = RoadBuilder(projection, sampler).create_decal_roads(roads)
            content.stats["decal_roads"] = len(content.decal_roads.get("roads", []))

        if buildings:
            mesh_builder = MeshBuilder(projection)
            mesh_dir = work_dir / "meshes"
            mesh_dir.mkdir(parents=True, exist_ok=True)

            placeable: list[dict] = []
            mesh_paths: list[str] = []
            for index, building in enumerate(buildings, start=1):
                collada = mesh_builder.build_mesh(building, index)
                if collada is None:
                    continue
                mesh_file = mesh_dir / f"building_{index:04d}.dae"
                mesh_file.write_text(collada, encoding="utf-8")

                placeable.append(building)
                content.mesh_files.append(str(mesh_file))
                # Path as the level will see it, once the exporter has copied
                # the mesh into the archive.
                mesh_paths.append(
                    f"levels/{work_dir.name}/art/shapes/buildings/{mesh_file.name}"
                )

            content.building_items = BuildingPlacer(projection, sampler).create_building_items(
                placeable, mesh_paths
            )
            content.stats["building_items"] = len(content.building_items)

        return content

    # -- AI stages ------------------------------------------------------------

    def _run_ai_stages(
        self,
        job_id: str,
        request: MapGenerationRequest,
        bbox: list[float],
        work_dir: Path,
        progress: ProgressReporter,
    ) -> dict[str, list] | None:
        """
        Fetch imagery and run AI segmentation.

        Returns ``None`` on failure: AI features are strictly additive, so a
        missing Ollama install degrades the result rather than failing the job.
        The failure is still reported on the job's stats so the UI can say why
        no roads were detected, instead of silently showing zero - which is
        what happened before, because a ``temp_dir`` NameError in this block
        was swallowed by a bare ``except`` and made AI segmentation fail 100%
        of the time with no visible cause.
        """
        try:
            progress.start("fetch_imagery")
            imagery_source = DataSourceFactory.get_imagery_source()
            rgb_image, _ = imagery_source.get_satellite_image(bbox=bbox, resolution=10)
            progress.finish("fetch_imagery", f"Imagery from {imagery_source.get_source_name()}")

            progress.start("segment")
            masks, feature_counts, detections = self._segment(rgb_image, bbox, work_dir)
            progress.finish("segment", f"AI detected {sum(feature_counts.values())} features")

            progress.start("vectorize")
            vector_data = self._vectorize(
                masks, bbox, rgb_image.shape[:2], work_dir, detections=detections
            )
            progress.finish("vectorize")

            self.job_store.update(
                job_id,
                stats={
                    "ai_enabled": True,
                    "roads": len(vector_data.get("roads", [])),
                    "buildings": len(vector_data.get("buildings", [])),
                },
            )
            return vector_data

        except _PROGRAMMING_ERRORS:
            # A NameError or TypeError here is a bug in this file, not a missing
            # Ollama install. Swallowing those is what hid the original
            # `temp_dir` NameError and made AI segmentation fail silently for
            # every user - and it caught a second one during this refactor.
            logger.exception("Bug in the AI segmentation stage")
            raise
        except Exception as exc:  # noqa: BLE001 - AI is optional, never fatal
            logger.warning("AI segmentation unavailable, continuing without it: %s", exc)
            self.job_store.update(
                job_id,
                stats={"ai_enabled": False, "ai_error": str(exc)[:300], "roads": 0, "buildings": 0},
            )
            # Credit the remaining AI stages so the progress bar still reaches 100.
            for stage in AI_STAGES:
                with suppress(KeyError):  # pragma: no cover - stage table mismatch
                    progress.finish(stage.key)
            return None

    def _segment(
        self, rgb_image: np.ndarray, bbox: list[float], work_dir: Path
    ) -> tuple[dict[str, np.ndarray], dict[str, int], dict[str, list]]:
        """
        Run the vision model and turn its output into raster masks.

        Returns the raw detections alongside the masks. Rasterising is lossy -
        a binary mask cannot carry a building's height - so the vectoriser
        needs the originals to restore those attributes.
        """
        from services.ai_segmentation.mask_generator import MaskGenerator
        from services.ai_segmentation.segmentor import AISegmentor

        segmentor = AISegmentor(model_name=self.settings.ollama_vl_model)
        try:
            # The pipeline runs in a worker thread with no event loop of its
            # own, so an isolated loop is created for the async client here.
            segmentation = asyncio.run(
                segmentor.segment_image(image=rgb_image, tasks=["roads", "buildings", "water", "forest"])
            )
            counts = segmentor.get_statistics(segmentation)
        finally:
            try:
                asyncio.run(segmentor.close())
            except Exception:  # noqa: BLE001 - closing must not mask a real error
                logger.debug("Ollama client close failed", exc_info=True)

        mask_dir = work_dir / "masks"
        mask_dir.mkdir(parents=True, exist_ok=True)

        generator = MaskGenerator(image_size=rgb_image.shape[:2])
        masks = generator.generate_masks(segmentation, bbox)
        generator.save_masks(masks, str(mask_dir))

        return masks, counts, segmentation

    def _vectorize(
        self,
        masks: dict[str, np.ndarray],
        bbox: list[float],
        image_size: tuple[int, int],
        work_dir: Path,
        detections: dict[str, list] | None = None,
    ) -> dict[str, list]:
        """Convert masks into GeoJSON feature collections on disk."""
        from services.vector_extraction.contour_extractor import ContourExtractor
        from services.vector_extraction.vectorizer import Vectorizer

        extractor = ContourExtractor()
        vectorizer = Vectorizer(bbox=bbox, image_size=image_size)

        vector_data: dict[str, list] = {}

        if "roads" in masks:
            centerlines = extractor.extract_centerlines(masks["roads"])
            # Widths measured from the mask, not a fixed pixel guess: the guess
            # turned a 9 m road into a 60 m one on a 6 km tile.
            widths = extractor.measure_widths(masks["roads"], centerlines)
            vector_data["roads"] = vectorizer.vectorize_road_network(
                centerlines, widths, source_features=(detections or {}).get("roads")
            )

        if "buildings" in masks:
            contours = extractor.extract_contours(masks["buildings"])
            polygons = extractor.contours_to_polygons(contours)
            # Height is not recoverable from a binary mask, so it is inherited
            # from the detection that produced each footprint.
            vector_data["buildings"] = vectorizer.vectorize_buildings(
                polygons,
                source_features=(detections or {}).get("buildings"),
            )

        geojson_dir = work_dir / "vectors"
        geojson_dir.mkdir(parents=True, exist_ok=True)
        for feature_type, features in vector_data.items():
            geojson = vectorizer.create_geojson(features, feature_type)
            (geojson_dir / f"{feature_type}.geojson").write_text(
                json.dumps(geojson, indent=2), encoding="utf-8"
            )

        return vector_data

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _resolve_dem_source(source_id: str) -> DataSourceInterface:
        """Resolve the requested data source identifier to a usable client."""
        if source_id == "auto":
            try:
                return DataSourceFactory.get_default_source()
            except NoDataSourceAvailableError as exc:
                # A missing API key is a configuration problem the user can fix,
                # so it surfaces as a readable job error rather than being
                # reported as an internal "unexpected error".
                raise PipelineError(str(exc)) from exc

        try:
            source_type = DataSourceType(source_id)
        except ValueError as exc:
            raise PipelineError(f"Unknown data source: {source_id}") from exc

        source = DataSourceFactory.create(source_type)

        if not source.provides(Capability.DEM):
            raise PipelineError(
                f"{source.get_source_name()} provides satellite imagery only. "
                f"Choose OpenTopography, Sentinel Hub, or 'auto' for elevation data."
            )

        if not source.is_available():
            raise PipelineError(
                f"{source.get_source_name()} is not configured. Add its credentials in "
                f"Settings, or choose 'auto' to use the best available source."
            )

        return source

    def _fail(self, job_id: str, message: str) -> None:
        self.job_store.update(
            job_id,
            status=JobStatus.FAILED,
            message="Map generation failed",
            error=message,
        )


def get_pipeline(job_store: JobStore) -> MapGenerationPipeline:
    """Build a pipeline bound to a job store."""
    return MapGenerationPipeline(job_store=job_store)


# Re-exported for callers that only need the type.
__all__ = [
    "MapGenerationPipeline",
    "PipelineError",
    "ProgressReporter",
    "Stage",
    "BASE_STAGES",
    "AI_STAGES",
    "get_pipeline",
]

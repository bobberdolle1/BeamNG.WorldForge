"""Pipeline orchestration: progress accounting, source selection, failure handling."""

from __future__ import annotations

import numpy as np
import pytest

from models.map_request import MapGenerationRequest
from services.data_sources.base import Capability, DataSourceInterface
from services.jobs import JobStatus
from services.pipeline import (
    AI_STAGES,
    BASE_STAGES,
    MapGenerationPipeline,
    PipelineError,
    ProgressReporter,
)


class FakeSource(DataSourceInterface):
    """In-memory data source so pipeline tests never touch the network."""

    capabilities = frozenset({Capability.DEM})

    def __init__(self, dem: np.ndarray, *, fail: Exception | None = None):
        super().__init__({})
        self._dem = dem
        self._fail = fail

    def get_dem_data(self, bbox, resolution=30):
        if self._fail:
            raise self._fail
        return self._dem, {"resolution": resolution}

    def get_satellite_image(self, bbox, resolution=10):
        raise NotImplementedError

    def test_connection(self):
        return True

    def requires_setup(self):
        return False

    def get_source_name(self):
        return "Fake DEM"


def make_request(**overrides) -> MapGenerationRequest:
    payload = {
        "name": "pipeline_test",
        "bbox": {
            "min_lat": 37.7749,
            "max_lat": 37.8049,
            "min_lon": -122.4294,
            "max_lon": -122.3994,
        },
        "resolution": 30,
        "heightmap_size": 256,
        "data_source": "auto",
        "use_ai_segmentation": False,
    }
    payload.update(overrides)
    return MapGenerationRequest(**payload)


# -- progress accounting --------------------------------------------------------


def test_progress_reaches_99_after_every_stage():
    """
    Progress must be a function of the stage table, not hand-written numbers.

    The old code hardcoded percentages at each call site, so enabling AI
    produced a bar that jumped backwards.
    """
    seen = []
    reporter = ProgressReporter(BASE_STAGES, lambda percent, _msg: seen.append(percent))

    for stage in BASE_STAGES:
        reporter.start(stage.key)
        reporter.finish(stage.key)

    assert seen == sorted(seen), "progress must never go backwards"
    assert seen[-1] == 99


def test_progress_is_monotonic_with_ai_stages_enabled():
    stages = BASE_STAGES[:2] + AI_STAGES + BASE_STAGES[2:]
    seen = []
    reporter = ProgressReporter(stages, lambda percent, _msg: seen.append(percent))

    for stage in stages:
        reporter.start(stage.key)
        reporter.finish(stage.key)

    assert seen == sorted(seen)
    assert seen[-1] == 99


def test_unknown_stage_is_a_programming_error():
    reporter = ProgressReporter(BASE_STAGES, lambda *_: None)
    with pytest.raises(KeyError):
        reporter.start("no_such_stage")


# -- end to end -----------------------------------------------------------------


def test_pipeline_produces_an_archive(settings, job_store, sample_dem, monkeypatch):
    pipeline = MapGenerationPipeline(job_store=job_store, settings=settings)
    monkeypatch.setattr(
        MapGenerationPipeline, "_resolve_dem_source", staticmethod(lambda _s: FakeSource(sample_dem))
    )

    job = job_store.create("pipeline_test")
    pipeline.run(job.job_id, make_request())

    finished = job_store.get(job.job_id)
    assert finished.status is JobStatus.COMPLETED, finished.error
    assert finished.progress == 100

    archive = finished.artifacts["archive"]
    assert archive.exists()
    assert archive.suffix == ".zip"
    assert finished.artifacts["preview"].exists()


def test_pipeline_records_terrain_stats(settings, job_store, sample_dem, monkeypatch):
    pipeline = MapGenerationPipeline(job_store=job_store, settings=settings)
    monkeypatch.setattr(
        MapGenerationPipeline, "_resolve_dem_source", staticmethod(lambda _s: FakeSource(sample_dem))
    )

    job = job_store.create("pipeline_test")
    pipeline.run(job.job_id, make_request())

    stats = job_store.get(job.job_id).stats
    assert stats["data_source"] == "Fake DEM"
    assert stats["terrain"]["min_elevation"] == pytest.approx(100.0, abs=0.5)


def test_pipeline_never_raises_on_failure(settings, job_store, sample_dem, monkeypatch):
    """
    A background task that raises dies silently and leaves the job wedged in
    'processing' forever, so the UI polls indefinitely.
    """
    monkeypatch.setattr(
        MapGenerationPipeline,
        "_resolve_dem_source",
        staticmethod(lambda _s: FakeSource(sample_dem, fail=RuntimeError("provider exploded"))),
    )
    pipeline = MapGenerationPipeline(job_store=job_store, settings=settings)

    job = job_store.create("pipeline_test")
    pipeline.run(job.job_id, make_request())  # must not raise

    finished = job_store.get(job.job_id)
    assert finished.status is JobStatus.FAILED
    assert "provider exploded" in finished.error


def test_ai_failure_degrades_instead_of_failing_the_job(
    settings, job_store, sample_dem, monkeypatch
):
    """
    AI is optional. A missing Ollama install must still yield a usable map -
    and, unlike before, must record *why* no features were detected instead of
    silently reporting zero.
    """
    monkeypatch.setattr(
        MapGenerationPipeline, "_resolve_dem_source", staticmethod(lambda _s: FakeSource(sample_dem))
    )
    monkeypatch.setattr(
        "services.data_sources.factory.DataSourceFactory.get_imagery_source",
        staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no imagery source"))),
    )

    pipeline = MapGenerationPipeline(job_store=job_store, settings=settings)
    job = job_store.create("pipeline_test")
    pipeline.run(job.job_id, make_request(use_ai_segmentation=True))

    finished = job_store.get(job.job_id)
    assert finished.status is JobStatus.COMPLETED, finished.error
    assert finished.progress == 100
    assert finished.stats["ai_enabled"] is False
    assert "no imagery source" in finished.stats["ai_error"]


# -- source resolution ----------------------------------------------------------


def test_imagery_only_source_is_rejected_for_dem(monkeypatch):
    class ImageryOnly(FakeSource):
        capabilities = frozenset({Capability.IMAGERY})

        def get_source_name(self):
            return "Azure Maps"

    monkeypatch.setattr(
        "services.data_sources.factory.DataSourceFactory.create",
        staticmethod(lambda *_args, **_kwargs: ImageryOnly(np.zeros((4, 4), dtype=np.float32))),
    )

    with pytest.raises(PipelineError, match="imagery only"):
        MapGenerationPipeline._resolve_dem_source("azure_maps")


def test_unknown_source_id_is_rejected():
    with pytest.raises(PipelineError, match="Unknown data source"):
        MapGenerationPipeline._resolve_dem_source("not_a_source")

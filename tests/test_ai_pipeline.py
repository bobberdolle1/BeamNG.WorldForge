"""
The optional AI path, end to end with the model stubbed.

Everything below the model call is the real code: parsing, rasterising,
tracing, vectorising, projecting and packaging. Only the inference is faked, so
a break anywhere in that chain shows up here rather than in a user's empty map.
"""

from __future__ import annotations

import json
import zipfile
from unittest.mock import patch

import numpy as np
import pytest

from models.map_request import MapGenerationRequest
from services.jobs import JobStatus, JobStore
from services.pipeline import MapGenerationPipeline

MODEL_REPLY = json.dumps(
    {
        "roads": [
            {
                "class": "road",
                "centerline": [[37.885, -122.61], [37.90, -122.59], [37.925, -122.57]],
                "width": 9.0,
            }
        ],
        "buildings": [
            {
                "footprint": [
                    [37.900, -122.600],
                    [37.9015, -122.600],
                    [37.9015, -122.5985],
                    [37.900, -122.5985],
                ],
                "height": 18.0,
            }
        ],
        "water": [],
        "forest": [],
    }
)


class FakeImagerySource:
    def get_satellite_image(self, bbox, resolution=10):
        return np.zeros((512, 512, 3), dtype=np.uint8), {}

    def get_source_name(self):
        return "Fake Imagery"


def make_request(**overrides) -> MapGenerationRequest:
    payload = {
        "name": "ai_map",
        "bbox": {
            "min_lat": 37.88,
            "max_lat": 37.94,
            "min_lon": -122.62,
            "max_lon": -122.55,
        },
        "resolution": 30,
        "heightmap_size": 512,
        "use_ai_segmentation": True,
    }
    payload.update(overrides)
    return MapGenerationRequest(**payload)


@pytest.fixture
def dem_source(sample_dem):
    from services.data_sources.base import Capability, DataSourceInterface

    class FakeDEM(DataSourceInterface):
        capabilities = frozenset({Capability.DEM})

        def get_dem_data(self, bbox, resolution=30):
            # Big enough that the heightmap is not mostly interpolation.
            grid = np.kron(sample_dem, np.ones((8, 8), dtype=np.float32))
            return grid, {"resolution": resolution}

        def get_satellite_image(self, bbox, resolution=10):
            raise NotImplementedError

        def test_connection(self):
            return True

        def requires_setup(self):
            return False

        def get_source_name(self):
            return "Fake DEM"

    return FakeDEM()


@pytest.fixture
def run_pipeline(settings, dem_source, monkeypatch):
    """Run the pipeline with the model reply and both data sources stubbed."""

    def runner(reply: str = MODEL_REPLY, **request_overrides):
        async def fake_generate(self, model, prompt, images=None, stream=False, options=None):
            return {"response": reply}

        monkeypatch.setattr(
            MapGenerationPipeline, "_resolve_dem_source", staticmethod(lambda _s: dem_source)
        )

        store = JobStore()
        pipeline = MapGenerationPipeline(job_store=store, settings=settings)
        request = make_request(**request_overrides)
        job = store.create(request.name)

        with patch("services.ollama.client.OllamaClient.generate", fake_generate), patch(
            "services.data_sources.factory.DataSourceFactory.get_imagery_source",
            staticmethod(lambda: FakeImagerySource()),
        ):
            pipeline.run(job.job_id, request)

        return store.get(job.job_id)

    return runner


def archive_entries(job) -> dict[str, bytes]:
    with zipfile.ZipFile(job.artifacts["archive"]) as zip_file:
        return {name: zip_file.read(name) for name in zip_file.namelist()}


# -- the happy path -------------------------------------------------------------


def test_detections_reach_the_packaged_level(run_pipeline):
    job = run_pipeline()

    assert job.status is JobStatus.COMPLETED, job.error
    assert job.stats["ai_enabled"] is True
    assert job.stats["roads"] >= 1
    assert job.stats["buildings"] >= 1
    assert job.stats["decal_roads"] >= 1
    assert job.stats["building_items"] >= 1

    entries = archive_entries(job)
    assert "levels/ai_map/decalRoad.json" in entries
    assert any(name.endswith(".dae") for name in entries)


def test_detected_attributes_survive_to_the_archive(run_pipeline):
    """A 9 m road and an 18 m building must still be 9 m and 18 m."""
    job = run_pipeline()
    entries = archive_entries(job)

    road = json.loads(entries["levels/ai_map/decalRoad.json"])["roads"][0]
    building = json.loads(entries["levels/ai_map/items.level.json"])["items"][0]

    assert road["nodes"][0]["width"] == pytest.approx(9.0)
    assert building["height"] == pytest.approx(18.0)


def test_placed_content_sits_inside_the_terrain_and_on_the_ground(run_pipeline):
    job = run_pipeline()
    entries = archive_entries(job)

    terrain = json.loads(entries["levels/ai_map/main.level.json"])["terrain"]
    floor = terrain["minHeight"]
    ceiling = floor + terrain["heightScale"]

    road = json.loads(entries["levels/ai_map/decalRoad.json"])["roads"][0]
    for node in road["nodes"]:
        x, y, z = node["pos"]
        assert abs(x) < 5_000 and abs(y) < 5_000
        assert floor <= z <= ceiling + 1

    building = json.loads(entries["levels/ai_map/items.level.json"])["items"][0]
    x, y, z = building["position"]
    assert abs(x) < 5_000 and abs(y) < 5_000
    assert floor <= z <= ceiling + 1


def test_meshes_referenced_by_items_are_packaged(run_pipeline):
    entries = archive_entries(run_pipeline())
    items = json.loads(entries["levels/ai_map/items.level.json"])["items"]

    assert items
    for item in items:
        assert item["shapeName"] in entries


# -- degradation ----------------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    [
        "I could not identify anything in this image.",
        "```json\n{broken\n```",
        "",
    ],
)
def test_an_unparseable_reply_still_produces_a_map(run_pipeline, reply):
    job = run_pipeline(reply=reply)

    assert job.status is JobStatus.COMPLETED, job.error
    assert job.stats["roads"] == 0
    assert job.stats["buildings"] == 0


def test_a_reply_with_no_detections_is_not_an_error(run_pipeline):
    job = run_pipeline(reply=json.dumps({"roads": [], "buildings": []}))

    assert job.status is JobStatus.COMPLETED
    assert job.stats["ai_enabled"] is True
    assert job.stats["roads"] == 0


def test_a_flat_list_reply_is_still_understood(run_pipeline):
    """Models often answer with a bare list instead of the requested object."""
    reply = json.dumps(
        [
            {
                "class": "road",
                "centerline": [[37.885, -122.61], [37.90, -122.59], [37.925, -122.57]],
                "width": 12.0,
            }
        ]
    )

    job = run_pipeline(reply=reply)
    assert job.stats["roads"] >= 1


def test_no_imagery_source_degrades_instead_of_failing(settings, dem_source, monkeypatch):
    monkeypatch.setattr(
        MapGenerationPipeline, "_resolve_dem_source", staticmethod(lambda _s: dem_source)
    )
    monkeypatch.setattr(
        "services.data_sources.factory.DataSourceFactory.get_imagery_source",
        staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no imagery configured"))),
    )

    store = JobStore()
    request = make_request()
    job = store.create(request.name)
    MapGenerationPipeline(job_store=store, settings=settings).run(job.job_id, request)

    finished = store.get(job.job_id)
    assert finished.status is JobStatus.COMPLETED
    assert finished.stats["ai_enabled"] is False
    assert "no imagery configured" in finished.stats["ai_error"]


def test_a_bug_in_the_ai_stage_is_not_swallowed(run_pipeline, monkeypatch):
    """
    The degrade-gracefully handler must not hide defects.

    A `NameError` in this block is what made AI segmentation fail silently for
    every user in the first place, and a second one slipped in while wiring
    attribute inheritance. Programming errors now propagate.
    """
    def explode(*args, **kwargs):
        raise NameError("name 'segmentation' is not defined")

    monkeypatch.setattr(MapGenerationPipeline, "_segment", explode)

    job = run_pipeline()

    assert job.status is JobStatus.FAILED
    assert "segmentation" in (job.error or "")

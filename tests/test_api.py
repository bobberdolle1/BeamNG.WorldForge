"""API surface: validation, job lifecycle, artefact serving, route precedence."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(settings, monkeypatch):
    """
    A TestClient with the data source layer stubbed out.

    Nothing here touches the network: the tests assert on the API's behaviour,
    not on whether Copernicus happens to be up today.
    """
    import main
    from services.jobs import job_store

    job_store.clear()

    with TestClient(main.app) as test_client:
        yield test_client

    job_store.clear()


@pytest.fixture
def stub_source(monkeypatch, sample_dem):
    """Replace source resolution with an in-memory fake DEM provider."""
    from services.data_sources.base import Capability, DataSourceInterface

    class FakeSource(DataSourceInterface):
        capabilities = frozenset({Capability.DEM, Capability.IMAGERY})

        def get_dem_data(self, bbox, resolution=30):
            return sample_dem, {"resolution": resolution, "source": "fake"}

        def get_satellite_image(self, bbox, resolution=10):
            return np.zeros((32, 32, 3), dtype=np.uint8), {}

        def test_connection(self):
            return True

        def requires_setup(self):
            return False

        def get_source_name(self):
            return "Fake Source"

    monkeypatch.setattr(
        "services.pipeline.MapGenerationPipeline._resolve_dem_source",
        staticmethod(lambda _source_id: FakeSource()),
    )
    return FakeSource


# -- health and routing ---------------------------------------------------------


def test_health_endpoint_is_reachable(client):
    """
    Regression: the SPA catch-all route was registered before /api/health, and
    FastAPI matches in registration order, so health checks 404'd in the
    bundled build.
    """
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unknown_api_path_returns_json_404_not_the_spa_shell(client):
    response = client.get("/api/definitely-not-a-real-endpoint")

    assert response.status_code == 404
    assert "text/html" not in response.headers.get("content-type", "")


def test_openapi_schema_is_served(client):
    assert client.get("/openapi.json").status_code == 200


# -- request validation ---------------------------------------------------------


def _payload(**overrides):
    body = {
        "name": "test_map",
        "bbox": {
            "min_lat": 37.7749,
            "max_lat": 37.8049,
            "min_lon": -122.4294,
            "max_lon": -122.3994,
        },
        "resolution": 30,
        "heightmap_size": 512,
        "data_source": "auto",
        "use_ai_segmentation": False,
    }
    body.update(overrides)
    return body


@pytest.mark.parametrize("name", ["..", "ab", "  ", "///", "../..", "...."])
def test_unusable_names_are_rejected(client, name):
    response = client.post("/api/generate", json=_payload(name=name))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "name",
    [
        "../../etc/passwd",
        "..\\..\\config\\settings.key",
        "map/../../secret",
        "a/b/c",
        "%2e%2e/%2e%2e/etc",
    ],
)
def test_traversal_input_never_yields_an_unsafe_name(client, stub_source, name):
    """
    Traversal attempts are neutralised, not merely rejected.

    Whether the request is refused or the name is slugified, the resulting map
    name must always be a plain slug that cannot escape the output directory.
    """
    from core.paths import is_valid_map_name

    response = client.post("/api/generate", json=_payload(name=name))

    assert response.status_code in (202, 422)
    if response.status_code == 202:
        assert is_valid_map_name(response.json()["map_name"])


def test_friendly_name_is_slugified(client, stub_source):
    response = client.post("/api/generate", json=_payload(name="San Francisco Downtown"))

    assert response.status_code == 202
    assert response.json()["map_name"] == "san_francisco_downtown"


def test_inverted_bbox_is_rejected(client):
    response = client.post(
        "/api/generate",
        json=_payload(
            bbox={"min_lat": 38.0, "max_lat": 37.0, "min_lon": -122.0, "max_lon": -123.0}
        ),
    )

    assert response.status_code == 422
    assert "min_lat" in response.json()["detail"]


def test_oversized_region_is_rejected_with_a_clear_message(client):
    response = client.post(
        "/api/generate",
        json=_payload(
            bbox={"min_lat": 30.0, "max_lat": 40.0, "min_lon": -122.0, "max_lon": -112.0}
        ),
    )

    assert response.status_code == 422
    assert "too large" in response.json()["detail"]


def test_non_power_of_two_heightmap_is_rejected(client):
    response = client.post("/api/generate", json=_payload(heightmap_size=1000))

    assert response.status_code == 422
    assert "power of two" in response.json()["detail"]


def test_validation_errors_are_flat_strings(client):
    """The UI renders `detail` directly; a list of dicts showed [object Object]."""
    detail = client.post("/api/generate", json=_payload(name="..")).json()["detail"]
    assert isinstance(detail, str)


# -- job lifecycle --------------------------------------------------------------


def test_generate_runs_to_completion(client, stub_source):
    response = client.post("/api/generate", json=_payload(name="pipeline_map"))
    assert response.status_code == 202

    job_id = response.json()["map_id"]

    # TestClient runs background tasks synchronously before returning, so the
    # job has already finished by the time we poll.
    status = client.get(f"/api/status/{job_id}").json()

    assert status["status"] == "completed", status.get("error")
    assert status["progress"] == 100
    assert status["download_url"] == f"/api/download/{job_id}"


def test_download_serves_a_real_zip(client, stub_source):
    job_id = client.post("/api/generate", json=_payload(name="zip_map")).json()["map_id"]

    response = client.get(f"/api/download/{job_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content[:2] == b"PK"


def test_preview_is_served_as_png(client, stub_source):
    job_id = client.post("/api/generate", json=_payload(name="preview_map")).json()["map_id"]

    response = client.get(f"/api/preview/{job_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_status_of_unknown_job_is_404(client):
    assert client.get("/api/status/00000000-0000-0000-0000-000000000000").status_code == 404


def test_download_of_unknown_job_is_404(client):
    assert client.get("/api/download/nope").status_code == 404


def test_failed_job_reports_the_reason(client, monkeypatch):
    from services.pipeline import PipelineError

    def explode(_source_id):
        raise PipelineError("OpenTopography is not configured")

    monkeypatch.setattr(
        "services.pipeline.MapGenerationPipeline._resolve_dem_source", staticmethod(explode)
    )

    job_id = client.post("/api/generate", json=_payload(name="failing_map")).json()["map_id"]
    status = client.get(f"/api/status/{job_id}").json()

    assert status["status"] == "failed"
    assert "not configured" in status["error"]

    # Downloading a failed job explains why rather than 404-ing.
    download = client.get(f"/api/download/{job_id}")
    assert download.status_code == 409


def test_jobs_can_be_listed_and_deleted(client, stub_source):
    job_id = client.post("/api/generate", json=_payload(name="deletable")).json()["map_id"]

    assert any(job["job_id"] == job_id for job in client.get("/api/jobs").json()["jobs"])

    assert client.delete(f"/api/jobs/{job_id}").status_code == 200
    assert client.get(f"/api/status/{job_id}").status_code == 404


# -- data sources ---------------------------------------------------------------


def test_data_sources_endpoint_lists_every_source(client):
    payload = client.get("/api/data-sources").json()

    ids = {source["id"] for source in payload["sources"]}
    assert {"sentinel_hub", "opentopography", "azure_maps", "google_earth_engine"} <= ids
    for source in payload["sources"]:
        assert isinstance(source["provides"], list)


def test_keyed_sources_report_unavailable_without_credentials(client):
    """
    With no credentials configured, every source that needs one is unavailable
    - and says so rather than raising.
    """
    payload = client.get("/api/data-sources").json()
    keyed = [source for source in payload["sources"] if source["id"] != "aws_terrain"]

    assert keyed, "expected several credentialed sources"
    assert all(source["available"] is False for source in keyed)


def test_aws_terrain_needs_no_setup(client):
    """
    The zero-config source is what makes a fresh clone usable.

    Availability is not asserted here because that would require reaching S3;
    what matters for the contract is that it advertises needing no setup.
    """
    payload = client.get("/api/data-sources").json()
    aws = next(source for source in payload["sources"] if source["id"] == "aws_terrain")

    assert aws["requires_setup"] is False
    assert aws["provides"] == ["dem"]


# -- settings -------------------------------------------------------------------


def test_settings_round_trip_masks_secrets(client):
    client.put(
        "/api/settings",
        json={"api_keys": {"opentopography_api_key": "abcdefgh1234"}},
    )

    keys = client.get("/api/settings").json()["api_keys"]
    assert keys["opentopography_api_key"] == "***1234"


def test_validate_endpoint_takes_credentials_in_the_body(client):
    """
    Regression: api_key used to be a query parameter, so every key a user
    tested was written into access logs and browser history.
    """
    response = client.post("/api/settings/validate/sentinel_hub", json={"api_key": "x"})

    # Missing secret is a validation failure, not a crash - and crucially the
    # endpoint accepts a JSON body at all.
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_validate_endpoint_rejects_unknown_service(client):
    response = client.post("/api/settings/validate/not_a_service", json={"api_key": "x"})
    assert response.status_code == 400


def test_validate_endpoint_requires_a_key(client):
    assert client.post("/api/settings/validate/sentinel_hub", json={}).status_code == 422

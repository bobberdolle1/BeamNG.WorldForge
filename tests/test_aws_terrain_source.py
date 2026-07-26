"""
AWS Terrain Tiles data source.

This is the source that makes a fresh clone usable without registering
anywhere, so its tile maths and mosaicking are worth pinning down. The
network-dependent test at the bottom is marked and excluded from CI.
"""

from __future__ import annotations

import io

import numpy as np
import pytest

from services.data_sources.aws_terrain_client import (
    MAX_TILES,
    TILE_SIZE,
    AWSTerrainDataSource,
    ground_resolution,
    lat_lon_to_tile,
    tile_to_lat_lon,
    zoom_for_resolution,
)
from services.data_sources.base import Capability

SF_BBOX = [-122.62, 37.88, -122.55, 37.94]


# -- tile maths -----------------------------------------------------------------


def test_zoom_zero_is_a_single_tile():
    assert lat_lon_to_tile(0.0, 0.0, 0) == (0, 0)
    assert lat_lon_to_tile(85.0, 179.0, 0) == (0, 0)


def test_tile_indices_round_trip():
    for zoom in (4, 8, 12):
        x, y = lat_lon_to_tile(37.9, -122.6, zoom)
        lat, lon = tile_to_lat_lon(x, y, zoom)
        # The corner of the containing tile is north-west of the point.
        assert lat >= 37.9 - 1
        assert lon <= -122.6 + 1
        assert lat_lon_to_tile(lat - 1e-6, lon + 1e-6, zoom) == (x, y)


@pytest.mark.parametrize("latitude", [-85.0, -45.0, 0.0, 45.0, 85.0])
def test_tile_indices_stay_in_range(latitude):
    zoom = 10
    for longitude in (-180.0, -0.0, 179.999):
        x, y = lat_lon_to_tile(latitude, longitude, zoom)
        assert 0 <= x < 2**zoom
        assert 0 <= y < 2**zoom


def test_poles_do_not_blow_up():
    """Web Mercator is undefined at the poles; the input must be clamped."""
    for latitude in (90.0, -90.0, 89.9999):
        x, y = lat_lon_to_tile(latitude, 0.0, 8)
        assert 0 <= x < 256 and 0 <= y < 256


def test_resolution_halves_with_each_zoom_level():
    assert ground_resolution(0.0, 11) == pytest.approx(ground_resolution(0.0, 10) / 2)


def test_resolution_shrinks_towards_the_poles():
    assert ground_resolution(60.0, 10) == pytest.approx(ground_resolution(0.0, 10) / 2, rel=0.01)


def test_finer_resolution_requests_a_deeper_zoom():
    assert zoom_for_resolution(SF_BBOX, 10) > zoom_for_resolution(SF_BBOX, 100)


def test_zoom_is_capped_by_the_tile_budget():
    """A large region must not silently request thousands of tiles."""
    continent = [-125.0, 25.0, -66.0, 49.0]
    zoom = zoom_for_resolution(continent, 10)

    x_min, y_max = lat_lon_to_tile(continent[1], continent[0], zoom)
    x_max, y_min = lat_lon_to_tile(continent[3], continent[2], zoom)
    tiles = (abs(x_max - x_min) + 1) * (abs(y_max - y_min) + 1)

    assert tiles <= MAX_TILES


# -- source behaviour -----------------------------------------------------------


def test_declares_elevation_only_and_no_setup():
    source = AWSTerrainDataSource()

    assert source.provides(Capability.DEM)
    assert not source.provides(Capability.IMAGERY)
    assert source.requires_setup() is False


def test_imagery_is_explicitly_unavailable():
    with pytest.raises(NotImplementedError, match="elevation only"):
        AWSTerrainDataSource().get_satellite_image(SF_BBOX)


def geotiff_bytes(fill: float) -> bytes:
    """A minimal single-band GeoTIFF, as the S3 bucket would serve."""
    import rasterio
    from rasterio.transform import from_origin

    buffer = io.BytesIO()
    with rasterio.open(
        buffer,
        "w",
        driver="GTiff",
        height=TILE_SIZE,
        width=TILE_SIZE,
        count=1,
        dtype="int16",
        crs="EPSG:3857",
        transform=from_origin(0, 0, 10, 10),
        nodata=-32768,
    ) as dataset:
        dataset.write(np.full((TILE_SIZE, TILE_SIZE), fill, dtype=np.int16), 1)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status_code: int, content: bytes = b"") -> None:
        self.status_code = status_code
        self.content = content


def test_mosaics_tiles_and_crops_to_the_request(monkeypatch):
    source = AWSTerrainDataSource()
    monkeypatch.setattr(
        source._session, "get", lambda *a, **k: FakeResponse(200, geotiff_bytes(250))
    )

    elevation, metadata = source.get_dem_data(SF_BBOX, resolution=30)

    assert elevation.ndim == 2
    assert np.nanmin(elevation) == pytest.approx(250.0)
    # Cropped to the request, so smaller than the full tile mosaic.
    assert elevation.shape[0] < TILE_SIZE * 8
    assert metadata["source"].startswith("AWS Terrain Tiles")
    assert metadata["tiles"] >= 1


def test_missing_tiles_become_voids_not_failures(monkeypatch):
    """S3 answers 403 for absent ocean tiles; that is 'no data', not an error."""
    source = AWSTerrainDataSource()

    calls = {"n": 0}

    def respond(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(403)
        return FakeResponse(200, geotiff_bytes(120))

    monkeypatch.setattr(source._session, "get", respond)

    elevation, _ = source.get_dem_data(SF_BBOX, resolution=30)
    assert np.isfinite(elevation).any()


def test_all_ocean_reports_an_actionable_error(monkeypatch):
    from services.data_sources.base import DataSourceError

    source = AWSTerrainDataSource()
    monkeypatch.setattr(source._session, "get", lambda *a, **k: FakeResponse(404))

    with pytest.raises(DataSourceError, match="open ocean"):
        source.get_dem_data(SF_BBOX, resolution=30)


def test_unexpected_status_is_reported(monkeypatch):
    from services.data_sources.base import DataSourceError

    source = AWSTerrainDataSource()
    monkeypatch.setattr(source._session, "get", lambda *a, **k: FakeResponse(500))

    with pytest.raises(DataSourceError, match="HTTP 500"):
        source.get_dem_data(SF_BBOX, resolution=30)


# -- live check -----------------------------------------------------------------


@pytest.mark.network
def test_live_fetch_returns_real_elevation():
    """
    Fetches Mount Tamalpais from the real bucket.

    Deselected in CI (`-m "not network"`); run it locally to confirm the
    dataset and its URL layout have not changed.
    """
    source = AWSTerrainDataSource()
    elevation, metadata = source.get_dem_data([-122.62, 37.88, -122.55, 37.94], resolution=30)

    # Mount Tamalpais is 784 m; the tile should peak within a few metres of it.
    assert 700 <= float(np.nanmax(elevation)) <= 850
    assert float(np.nanmin(elevation)) >= -20
    assert metadata["zoom"] >= 10

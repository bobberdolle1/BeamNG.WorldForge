"""Geographic helpers and application configuration."""

from __future__ import annotations

import pytest

from core.geo import bbox_dimensions, meters_per_degree_lon, pixel_dimensions
from models.map_request import BoundingBox


def test_one_degree_of_latitude_is_about_111_km():
    dimensions = bbox_dimensions(0.0, 0.0, 0.0001, 1.0)
    assert dimensions.height_meters == pytest.approx(111_320, rel=0.001)


def test_longitude_shrinks_towards_the_poles():
    assert meters_per_degree_lon(0.0) == pytest.approx(111_320, rel=0.001)
    assert meters_per_degree_lon(60.0) == pytest.approx(111_320 / 2, rel=0.01)
    assert meters_per_degree_lon(89.0) < 2_000


def test_san_francisco_box_area_is_plausible(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    dimensions = bbox_dimensions(min_lon, min_lat, max_lon, max_lat)

    # 0.03 deg lat x 0.03 deg lon at 37.8N: roughly 3.3 x 2.6 km.
    assert dimensions.height_meters == pytest.approx(3_340, rel=0.05)
    assert dimensions.width_meters == pytest.approx(2_640, rel=0.05)
    assert dimensions.area_km2 == pytest.approx(8.8, rel=0.05)


def test_pixel_dimensions_respect_resolution(bbox):
    coarse = pixel_dimensions(bbox, 30)
    fine = pixel_dimensions(bbox, 10)

    assert fine[0] > coarse[0]
    assert fine[1] > coarse[1]


def test_pixel_dimensions_clamp_to_max(bbox):
    width, height = pixel_dimensions(bbox, 1, max_size=512)
    assert max(width, height) <= 512


def test_pixel_dimensions_clamp_to_min():
    tiny = [0.0, 0.0, 0.0001, 0.0001]
    width, height = pixel_dimensions(tiny, 30, min_size=256)
    assert (width, height) == (256, 256)


def test_pixel_dimensions_rejects_zero_resolution(bbox):
    with pytest.raises(ValueError):
        pixel_dimensions(bbox, 0)


# -- request model --------------------------------------------------------------


def test_bounding_box_area_matches_geo_helper(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    box = BoundingBox(min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon)

    assert box.area_km2 == pytest.approx(8.8, rel=0.05)
    assert box.to_list() == bbox


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_lat": 38.0, "max_lat": 37.0, "min_lon": -122.4, "max_lon": -122.3},
        {"min_lat": 37.0, "max_lat": 37.1, "min_lon": -122.3, "max_lon": -122.4},
        {"min_lat": 37.0, "max_lat": 37.0, "min_lon": -122.4, "max_lon": -122.3},
    ],
)
def test_degenerate_boxes_are_rejected(kwargs):
    with pytest.raises(ValueError):
        BoundingBox(**kwargs)


def test_huge_box_is_rejected():
    with pytest.raises(ValueError, match="too large"):
        BoundingBox(min_lat=30.0, max_lat=40.0, min_lon=-122.0, max_lon=-112.0)


def test_microscopic_box_is_rejected():
    with pytest.raises(ValueError, match="too small"):
        BoundingBox(min_lat=37.0, max_lat=37.00001, min_lon=-122.0, max_lon=-121.99999)


# -- settings -------------------------------------------------------------------


def test_directories_are_absolute_regardless_of_cwd(settings):
    """
    Paths used to be resolved against the process cwd, so a generated map
    landed wherever the server happened to be started from.
    """
    assert settings.output_dir.is_absolute()
    assert settings.temp_dir.is_absolute()
    assert settings.config_dir.is_absolute()


def test_cors_origins_parse_into_a_list(monkeypatch):
    from core import config as config_module

    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test ,")
    config_module.get_settings.cache_clear()

    assert config_module.get_settings().cors_origin_list == ["http://a.test", "http://b.test"]
    config_module.get_settings.cache_clear()


def test_invalid_log_level_fails_loudly(monkeypatch):
    from core import config as config_module

    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
    config_module.get_settings.cache_clear()

    with pytest.raises(ValueError, match="log_level"):
        config_module.get_settings()

    config_module.get_settings.cache_clear()


def test_ollama_host_env_var_is_honoured(monkeypatch):
    """
    .env.example documented OLLAMA_HOST while the client read OLLAMA_BASE_URL,
    so following the documentation had no effect.
    """
    from core import config as config_module

    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.internal:11434")
    config_module.get_settings.cache_clear()

    assert config_module.get_settings().ollama_base_url == "http://ollama.internal:11434"
    config_module.get_settings.cache_clear()

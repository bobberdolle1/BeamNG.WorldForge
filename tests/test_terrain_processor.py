"""Terrain processing: nodata handling, normalisation, and heightmap output."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from models.terrain import HeightmapConfig, TerrainData
from services.terrain.processor import TerrainProcessingError, TerrainProcessor


@pytest.fixture
def processor():
    return TerrainProcessor()


def test_process_dem_keeps_elevation_range(processor, sample_dem):
    terrain = processor.process_dem(sample_dem)

    assert terrain.width == sample_dem.shape[1]
    assert terrain.height == sample_dem.shape[0]
    assert terrain.min_elevation == pytest.approx(float(sample_dem.min()), abs=0.01)
    assert terrain.max_elevation == pytest.approx(float(sample_dem.max()), abs=0.01)
    assert terrain.nodata_fraction == 0.0


def test_nodata_is_filled_from_neighbours_not_zeroed(processor, sample_dem):
    """
    The regression this guards against: nodata used to become 0 m.

    On a plateau at 100-340 m that produced a 340 m cliff at every voided
    pixel, and normalising against the resulting min/max squashed the real
    terrain into a fraction of the available bit depth.
    """
    dem = sample_dem.copy()
    dem[10:14, 20:26] = np.nan
    dem[30, 40] = -32768.0  # SRTM void sentinel

    terrain = processor.process_dem(dem)

    assert terrain.nodata_fraction > 0
    assert np.isfinite(terrain.elevation).all()
    # Filled values stay inside the range of the real data around them.
    assert terrain.min_elevation >= 99.0
    assert terrain.max_elevation <= float(np.nanmax(sample_dem)) + 0.01


def test_process_dem_rejects_all_nodata(processor):
    with pytest.raises(TerrainProcessingError, match="no valid elevation"):
        processor.process_dem(np.full((16, 16), np.nan, dtype=np.float32))


def test_process_dem_rejects_empty_and_non_2d(processor):
    with pytest.raises(TerrainProcessingError):
        processor.process_dem(np.array([], dtype=np.float32).reshape(0, 0))
    with pytest.raises(TerrainProcessingError):
        processor.process_dem(np.zeros((4, 4, 3), dtype=np.float32))


@pytest.mark.parametrize("size", [256, 512, 1024])
def test_heightmap_has_exact_requested_size(processor, sample_dem, size):
    terrain = processor.process_dem(sample_dem)
    heightmap = processor.generate_heightmap(terrain, HeightmapConfig(size=size))

    assert heightmap.shape == (size, size)
    assert heightmap.dtype == np.uint16


def test_heightmap_uses_full_bit_depth(processor, sample_dem):
    terrain = processor.process_dem(sample_dem)
    heightmap = processor.generate_heightmap(terrain, HeightmapConfig(size=256))

    assert heightmap.min() == 0
    assert heightmap.max() == 65535


def test_flat_terrain_does_not_divide_by_zero(processor):
    flat = np.full((32, 32), 42.0, dtype=np.float32)
    terrain = processor.process_dem(flat)
    heightmap = processor.generate_heightmap(terrain, HeightmapConfig(size=64))

    assert heightmap.shape == (64, 64)
    assert np.all(heightmap == 0)


def test_preview_of_flat_terrain_renders(processor, tmp_path):
    """Flat terrain gives an all-zero heightmap; the preview used to divide by it."""
    output = tmp_path / "preview.png"
    processor.generate_preview(np.zeros((32, 32), dtype=np.uint16), output)

    assert output.exists()
    with Image.open(output) as image:
        assert image.size[0] > 0


def test_saved_heightmap_is_16_bit_grayscale(processor, sample_dem, tmp_path):
    terrain = processor.process_dem(sample_dem)
    heightmap = processor.generate_heightmap(terrain, HeightmapConfig(size=256))
    path = processor.save_heightmap(heightmap, tmp_path / "hm.png", bit_depth=16)

    with Image.open(path) as image:
        assert image.mode == "I;16"
        assert image.size == (256, 256)


def test_vertical_scale_does_not_change_normalised_output(processor, sample_dem):
    """
    Scaling every sample by a constant cannot change a min/max normalisation.

    Worth pinning: it documents that vertical_scale belongs in the level
    metadata (heightScale), not in the image.
    """
    terrain = processor.process_dem(sample_dem)
    plain = processor.generate_heightmap(terrain, HeightmapConfig(size=128, vertical_scale=1.0))
    scaled = processor.generate_heightmap(terrain, HeightmapConfig(size=128, vertical_scale=3.0))

    assert np.array_equal(plain, scaled)


def test_heightmap_config_rejects_non_power_of_two():
    with pytest.raises(ValueError, match="power of two"):
        HeightmapConfig(size=1000)


def test_terrain_data_rejects_bad_shapes():
    with pytest.raises(ValueError):
        TerrainData(elevation=np.zeros((2, 2, 2)))
    with pytest.raises(ValueError):
        TerrainData(elevation=np.array([]).reshape(0, 0))

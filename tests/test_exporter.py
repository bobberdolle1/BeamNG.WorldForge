"""BeamNG mod export: archive layout, metadata correctness, name safety."""

from __future__ import annotations

import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from models.terrain import TerrainData
from services.export.beamng_exporter import BeamNGExporter


@pytest.fixture
def heightmap_file(tmp_path):
    data = (np.linspace(0, 65535, 1024 * 1024).reshape(1024, 1024)).astype(np.uint16)
    path = tmp_path / "heightmap.png"
    Image.fromarray(data).save(path)
    return path


@pytest.fixture
def preview_file(tmp_path):
    path = tmp_path / "preview.png"
    Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8)).save(path)
    return path


@pytest.fixture
def terrain(sample_dem):
    return TerrainData.from_numpy(sample_dem)


def read_archive(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_archive_contains_expected_layout(settings, heightmap_file, preview_file, terrain, bbox):
    exporter = BeamNGExporter(settings.output_dir)
    archive_path = exporter.create_map_structure(
        map_name="test_map",
        heightmap_path=heightmap_file,
        preview_path=preview_file,
        terrain=terrain,
        bbox=bbox,
        source_name="OpenTopography",
    )

    entries = read_archive(archive_path)
    for expected in (
        "levels/test_map/info.json",
        "levels/test_map/main.level.json",
        "levels/test_map/items.level.json",
        "levels/test_map/preview.png",
        "levels/test_map/WORLDFORGE.md",
        "levels/test_map/art/terrains/main_terrain/heightmap.png",
        "levels/test_map/art/terrains/main_terrain/layers.json",
    ):
        assert expected in entries, f"missing {expected}"


def test_preview_is_actually_included(settings, heightmap_file, preview_file, terrain, bbox):
    """
    Regression: preview_path was accepted and then never used.

    info.json referenced a preview file that was not in the archive, so the
    level showed a blank thumbnail in game.
    """
    exporter = BeamNGExporter(settings.output_dir)
    archive_path = exporter.create_map_structure(
        map_name="with_preview",
        heightmap_path=heightmap_file,
        preview_path=preview_file,
        terrain=terrain,
        bbox=bbox,
    )

    entries = read_archive(archive_path)
    info = json.loads(entries["levels/with_preview/info.json"])

    for referenced in info["previews"]:
        assert f"levels/with_preview/{referenced}" in entries


def test_square_size_scales_with_region(settings, heightmap_file, terrain):
    """
    squareSize was hardcoded to 2.0, so a 1 km box and a 10 km box produced
    identically sized terrain. It must now track the selected region.
    """
    exporter = BeamNGExporter(settings.output_dir)

    small_bbox = [-122.40, 37.77, -122.39, 37.78]  # ~1 km
    large_bbox = [-122.50, 37.70, -122.40, 37.80]  # ~10 km

    small = json.loads(
        read_archive(
            exporter.create_map_structure("small_map", heightmap_file, terrain=terrain, bbox=small_bbox)
        )["levels/small_map/main.level.json"]
    )
    large = json.loads(
        read_archive(
            exporter.create_map_structure("large_map", heightmap_file, terrain=terrain, bbox=large_bbox)
        )["levels/large_map/main.level.json"]
    )

    assert large["terrain"]["squareSize"] > small["terrain"]["squareSize"] * 5


def test_level_json_records_real_elevation(settings, heightmap_file, terrain, bbox):
    exporter = BeamNGExporter(settings.output_dir)
    archive_path = exporter.create_map_structure(
        "elev_map", heightmap_file, terrain=terrain, bbox=bbox
    )

    level = json.loads(read_archive(archive_path)["levels/elev_map/main.level.json"])

    assert level["terrain"]["minHeight"] == pytest.approx(terrain.min_elevation, abs=0.01)
    assert level["terrain"]["heightScale"] == pytest.approx(terrain.elevation_range, abs=0.01)


@pytest.mark.parametrize("bad_name", ["../escape", "has space", "UPPER", "..", "a"])
def test_unsafe_map_names_are_refused(settings, heightmap_file, bad_name):
    exporter = BeamNGExporter(settings.output_dir)
    with pytest.raises(ValueError, match="unsafe map name"):
        exporter.create_map_structure(bad_name, heightmap_file)


def test_missing_heightmap_raises(settings, tmp_path):
    exporter = BeamNGExporter(settings.output_dir)
    with pytest.raises(FileNotFoundError):
        exporter.create_map_structure("missing_map", tmp_path / "nope.png")


def test_staging_directory_is_cleaned_up(settings, heightmap_file, terrain, bbox):
    exporter = BeamNGExporter(settings.output_dir)
    exporter.create_map_structure("clean_map", heightmap_file, terrain=terrain, bbox=bbox)

    assert not (settings.output_dir / ".staging" / "clean_map").exists()


def test_export_is_reproducible(settings, heightmap_file, terrain, bbox):
    """Same input twice produces the same file list, in the same order."""
    exporter = BeamNGExporter(settings.output_dir)

    first = exporter.create_map_structure("repeat_map", heightmap_file, terrain=terrain, bbox=bbox)
    with zipfile.ZipFile(first) as archive:
        names_first = archive.namelist()

    second = exporter.create_map_structure("repeat_map", heightmap_file, terrain=terrain, bbox=bbox)
    with zipfile.ZipFile(second) as archive:
        names_second = archive.namelist()

    assert names_first == names_second


def test_vector_data_is_written_when_present(settings, heightmap_file, terrain, bbox):
    exporter = BeamNGExporter(settings.output_dir)
    archive_path = exporter.create_map_structure(
        "vector_map",
        heightmap_file,
        terrain=terrain,
        bbox=bbox,
        vector_data={"roads": [{"id": 1}], "buildings": []},
    )

    entries = read_archive(archive_path)
    assert "levels/vector_map/vectors/roads.json" in entries
    assert json.loads(entries["levels/vector_map/vectors/roads.json"])["features"] == [{"id": 1}]

"""
Whole-archive validation.

Checks the internal consistency of a generated mod: that every path referenced
by the level metadata is actually present, that the JSON parses, and that the
terrain files agree with each other. These are the properties that can be
verified without launching the game - and they are exactly the ones that broke
before (``info.json`` pointing at a preview that was never packaged).
"""

from __future__ import annotations

import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from models.terrain import TerrainData
from services.export.beamng_exporter import BeamNGExporter
from services.export.terrain_file import TER_VERSION, read_ter

SF_BBOX = [-122.62, 37.88, -122.55, 37.94]
MAP_NAME = "archive_map"


@pytest.fixture
def archive(settings, tmp_path, sample_dem):
    """A complete mod archive with roads, buildings and meshes."""
    heights = np.linspace(0, 65535, 1024 * 1024).reshape(1024, 1024).astype(np.uint16)
    heightmap_path = tmp_path / "heightmap.png"
    Image.fromarray(heights).save(heightmap_path)

    preview_path = tmp_path / "preview.png"
    Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8)).save(preview_path)

    mesh_path = tmp_path / "building_0001.dae"
    mesh_path.write_text("<?xml version='1.0'?><COLLADA/>", encoding="utf-8")

    exporter = BeamNGExporter(settings.output_dir)
    return exporter.create_map_structure(
        map_name=MAP_NAME,
        heightmap_path=heightmap_path,
        preview_path=preview_path,
        terrain=TerrainData.from_numpy(sample_dem),
        bbox=SF_BBOX,
        source_name="AWS Terrain Tiles",
        decal_roads={"version": 1, "roads": [{"name": "road_0001", "nodes": []}]},
        building_items=[
            {
                "class": "TSStatic",
                "name": "building_0001",
                "shapeName": f"levels/{MAP_NAME}/art/shapes/buildings/building_0001.dae",
                "position": [10.0, 20.0, 130.0],
            }
        ],
        mesh_files=[str(mesh_path)],
    )


@pytest.fixture
def entries(archive) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as zip_file:
        return {name: zip_file.read(name) for name in zip_file.namelist()}


def level_path(*parts: str) -> str:
    return "/".join(("levels", MAP_NAME, *parts))


# -- structure ------------------------------------------------------------------


def test_every_json_file_parses(entries):
    for name, payload in entries.items():
        if name.endswith(".json"):
            json.loads(payload)


def test_all_content_lives_under_the_level_directory(entries):
    for name in entries:
        assert name.startswith(f"levels/{MAP_NAME}/"), f"{name} escapes the level directory"


def test_archive_has_no_absolute_or_traversing_paths(archive):
    with zipfile.ZipFile(archive) as zip_file:
        for name in zip_file.namelist():
            assert not name.startswith("/")
            assert ".." not in name.split("/")


# -- referential integrity ------------------------------------------------------


def test_preview_referenced_by_info_json_is_packaged(entries):
    info = json.loads(entries[level_path("info.json")])
    for preview in info["previews"]:
        assert level_path(preview) in entries


def test_terrain_files_referenced_by_the_level_are_packaged(entries):
    level = json.loads(entries[level_path("main.level.json")])["terrain"]

    assert level_path(level["terrainFile"]) in entries
    assert level_path(level["heightmapImage"]) in entries


def test_every_item_shape_is_packaged(entries):
    items = json.loads(entries[level_path("items.level.json")])["items"]

    assert items, "expected the building item to be present"
    for item in items:
        assert item["shapeName"] in entries, f"missing mesh {item['shapeName']}"


def test_terrain_layer_materials_are_declared(entries):
    layers = json.loads(entries[level_path("art/terrains/main_terrain/layers.json")])
    declared = {material["name"] for material in layers["materials"]}

    for layer in layers["layers"]:
        assert layer["material"] in declared


# -- terrain --------------------------------------------------------------------


def test_heightmap_is_square_16_bit(entries, tmp_path):
    png = tmp_path / "hm.png"
    png.write_bytes(entries[level_path("art/terrains/main_terrain/heightmap.png")])

    with Image.open(png) as image:
        assert image.mode == "I;16"
        assert image.size[0] == image.size[1]


def test_binary_terrain_matches_the_heightmap(entries, tmp_path):
    ter = tmp_path / "t.ter"
    ter.write_bytes(entries[level_path("art/terrains/main_terrain/main_terrain.ter")])
    png = tmp_path / "hm.png"
    png.write_bytes(entries[level_path("art/terrains/main_terrain/heightmap.png")])

    heights, _, materials = read_ter(ter)
    with Image.open(png) as image:
        expected = np.array(image)

    assert ter.read_bytes()[0] == TER_VERSION
    assert np.array_equal(heights, expected)
    assert materials


def test_terrain_scale_matches_the_selected_region(entries):
    """squareSize x heightmap size must equal the real ground size."""
    level = json.loads(entries[level_path("main.level.json")])["terrain"]
    info = entries[level_path("art/terrains/main_terrain/heightmap.png")]

    from io import BytesIO

    with Image.open(BytesIO(info)) as image:
        pixels = image.size[0]

    from core.geo import bbox_dimensions

    expected = bbox_dimensions(*SF_BBOX).max_side_meters
    assert level["squareSize"] * pixels == pytest.approx(expected, rel=0.01)


def test_elevation_metadata_is_present_and_sane(entries):
    level = json.loads(entries[level_path("main.level.json")])["terrain"]

    assert level["heightScale"] > 0
    assert -500 < level["minHeight"] < 9000


# -- optional content -----------------------------------------------------------


def test_roads_are_packaged_when_detected(entries):
    assert level_path("decalRoad.json") in entries
    assert json.loads(entries[level_path("decalRoad.json")])["roads"]


def test_provenance_notes_are_included(entries):
    notes = entries[level_path("WORLDFORGE.md")].decode("utf-8")

    assert "AWS Terrain Tiles" in notes
    assert "World Editor" in notes, "the manual import fallback must stay documented"


def test_a_bare_export_still_produces_a_valid_archive(settings, tmp_path):
    """No roads, no buildings, no preview - the common case must still work."""
    heights = np.zeros((512, 512), dtype=np.uint16)
    heightmap_path = tmp_path / "flat.png"
    Image.fromarray(heights).save(heightmap_path)

    archive = BeamNGExporter(settings.output_dir).create_map_structure(
        map_name="bare_map", heightmap_path=heightmap_path
    )

    with zipfile.ZipFile(archive) as zip_file:
        names = zip_file.namelist()
        for required in ("info.json", "main.level.json", "items.level.json"):
            assert f"levels/bare_map/{required}" in names
        assert json.loads(zip_file.read("levels/bare_map/items.level.json"))["items"] == []

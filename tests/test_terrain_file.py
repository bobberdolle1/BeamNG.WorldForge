"""
Binary ``.ter`` terrain writer.

What can and cannot be verified here: the byte layout, the round trip, and the
validation rules are all checkable. Whether BeamNG actually accepts the file is
not - that needs the game. The writer follows the community-documented format
and the archive still ships the PNG, so a rejected ``.ter`` costs a manual
World Editor import rather than a broken level.
"""

from __future__ import annotations

import struct

import numpy as np
import pytest

from services.export.terrain_file import (
    TER_VERSION,
    TerrainFileError,
    read_ter,
    write_ter,
)


@pytest.fixture
def heightmap() -> np.ndarray:
    return np.linspace(0, 65535, 128 * 128).reshape(128, 128).astype(np.uint16)


def test_round_trip_preserves_heights(tmp_path, heightmap):
    path = write_ter(tmp_path / "t.ter", heightmap)
    heights, indices, materials = read_ter(path)

    assert np.array_equal(heights, heightmap)
    assert indices.shape == heightmap.shape
    assert materials == ["grass"]


def test_header_matches_the_documented_layout(tmp_path, heightmap):
    path = write_ter(tmp_path / "t.ter", heightmap)
    data = path.read_bytes()

    assert struct.unpack_from("<B", data, 0)[0] == TER_VERSION
    assert struct.unpack_from("<I", data, 1)[0] == 128


def test_file_size_is_exactly_what_the_layout_implies(tmp_path, heightmap):
    path = write_ter(tmp_path / "t.ter", heightmap, material_names=["grass", "rock"])

    cells = 128 * 128
    expected = (
        1                       # version
        + 4                     # size
        + cells * 2             # uint16 heights
        + cells                 # uint8 material indices
        + 4                     # material count
        + (1 + len("grass"))
        + (1 + len("rock"))
    )
    assert path.stat().st_size == expected


def test_heights_are_little_endian_regardless_of_host(tmp_path):
    heights = np.array([[0x0102, 0], [0, 0]], dtype=np.uint16)
    heights = np.pad(heights, ((0, 62), (0, 62)))  # 64x64, the minimum size

    path = write_ter(tmp_path / "t.ter", heights.astype(np.uint16))
    data = path.read_bytes()

    # First height word follows the 5-byte header, low byte first.
    assert data[5] == 0x02
    assert data[6] == 0x01


def test_material_indices_round_trip(tmp_path, heightmap):
    indices = np.zeros((128, 128), dtype=np.uint8)
    indices[64:, :] = 1

    path = write_ter(
        tmp_path / "t.ter", heightmap, material_names=["grass", "rock"], material_indices=indices
    )
    _, read_back, materials = read_ter(path)

    assert np.array_equal(read_back, indices)
    assert materials == ["grass", "rock"]


@pytest.mark.parametrize(
    ("shape", "message"),
    [
        ((128, 64), "square"),
        ((32, 32), "at least"),
        ((100, 100), "power of two"),
    ],
)
def test_invalid_terrain_shapes_are_rejected(tmp_path, shape, message):
    with pytest.raises(TerrainFileError, match=message):
        write_ter(tmp_path / "t.ter", np.zeros(shape, dtype=np.uint16))


def test_non_2d_input_is_rejected(tmp_path):
    with pytest.raises(TerrainFileError, match="2D"):
        write_ter(tmp_path / "t.ter", np.zeros((64, 64, 3), dtype=np.uint16))


def test_undeclared_material_index_is_rejected(tmp_path, heightmap):
    indices = np.full((128, 128), 3, dtype=np.uint8)

    with pytest.raises(TerrainFileError, match="not declared"):
        write_ter(tmp_path / "t.ter", heightmap, material_names=["grass"], material_indices=indices)


def test_mismatched_material_grid_is_rejected(tmp_path, heightmap):
    with pytest.raises(TerrainFileError, match="does not match"):
        write_ter(
            tmp_path / "t.ter",
            heightmap,
            material_indices=np.zeros((64, 64), dtype=np.uint8),
        )


def test_non_ascii_material_name_is_rejected(tmp_path, heightmap):
    with pytest.raises(TerrainFileError, match="ASCII"):
        write_ter(tmp_path / "t.ter", heightmap, material_names=["трава"])


def test_reading_an_unknown_version_fails_loudly(tmp_path, heightmap):
    path = write_ter(tmp_path / "t.ter", heightmap)
    data = bytearray(path.read_bytes())
    data[0] = 99
    path.write_bytes(bytes(data))

    with pytest.raises(TerrainFileError, match="version"):
        read_ter(path)

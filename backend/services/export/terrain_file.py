"""
Write BeamNG's binary ``.ter`` terrain file.

**Why this exists.** BeamNG does not load a PNG heightmap at runtime. A level's
terrain is a binary ``.ter`` blob referenced by a ``TerrainBlock`` object; the
World Editor's "Import Heightmap" command is what converts a PNG into one. So
an archive containing only ``heightmap.png`` is not a drop-in mod - it needs a
manual import step before it can be driven on.

**Confidence.** The layout below follows the format as documented by the
BeamNG modding community and as implemented by third-party terrain tools. It
has *not* been verified by loading a generated level in the game from this
environment. The PNG is still written alongside it, so if the ``.ter`` is
rejected the manual import path remains available and nothing is lost.

Layout, little-endian throughout::

    uint8              version (8)
    uint32             size            terrain is size x size
    uint16[size*size]  heights         row-major, north-west origin
    uint8[size*size]   material index  per cell, into the material list
    uint32             materialCount
    repeated:
        uint8          name length
        char[n]        material name (ASCII)
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from core.logging_config import get_logger

logger = get_logger(__name__)

#: Format revision understood by current BeamNG releases.
TER_VERSION = 8

#: Terrain must be square and power-of-two, same constraint as the heightmap.
MIN_SIZE = 64


class TerrainFileError(ValueError):
    """Raised when terrain data cannot be written as a ``.ter`` file."""


def write_ter(
    path: Path,
    heightmap: np.ndarray,
    material_names: list[str] | None = None,
    material_indices: np.ndarray | None = None,
) -> Path:
    """
    Write a ``.ter`` terrain file.

    Args:
        path: Destination file.
        heightmap: Square ``uint16`` heightmap, north-west origin.
        material_names: Terrain materials, in index order. Defaults to a single
            grass layer.
        material_indices: Per-cell material index. Defaults to all zeros, i.e.
            the first material everywhere.

    Returns:
        The path written to.

    Raises:
        TerrainFileError: If the heightmap is not square, too small, or not
            power-of-two sized.
    """
    heights = np.asarray(heightmap)

    if heights.ndim != 2:
        raise TerrainFileError(f"heightmap must be 2D, got shape {heights.shape}")
    if heights.shape[0] != heights.shape[1]:
        raise TerrainFileError(f"terrain must be square, got {heights.shape}")

    size = int(heights.shape[0])
    if size < MIN_SIZE:
        raise TerrainFileError(f"terrain must be at least {MIN_SIZE}x{MIN_SIZE}, got {size}")
    if size & (size - 1) != 0:
        raise TerrainFileError(f"terrain size must be a power of two, got {size}")

    materials = list(material_names) if material_names else ["grass"]
    for name in materials:
        if not name.isascii():
            raise TerrainFileError(f"material name must be ASCII: {name!r}")
        if not 0 < len(name) < 256:
            raise TerrainFileError(f"material name length must be 1-255: {name!r}")

    if material_indices is None:
        indices = np.zeros((size, size), dtype=np.uint8)
    else:
        indices = np.asarray(material_indices, dtype=np.uint8)
        if indices.shape != heights.shape:
            raise TerrainFileError(
                f"material index grid {indices.shape} does not match heightmap {heights.shape}"
            )
        if int(indices.max(initial=0)) >= len(materials):
            raise TerrainFileError("material index refers to a material that was not declared")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as handle:
        handle.write(struct.pack("<B", TER_VERSION))
        handle.write(struct.pack("<I", size))
        # `astype` with an explicit little-endian dtype keeps the output
        # identical on big-endian hosts.
        handle.write(heights.astype("<u2").tobytes(order="C"))
        handle.write(indices.astype(np.uint8).tobytes(order="C"))
        handle.write(struct.pack("<I", len(materials)))
        for name in materials:
            encoded = name.encode("ascii")
            handle.write(struct.pack("<B", len(encoded)))
            handle.write(encoded)

    logger.info("Wrote terrain file: %s (%d x %d)", path, size, size)
    return path


def read_ter(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Read back a ``.ter`` file.

    Exists so the writer can be verified by round-trip rather than by
    inspection - the one property that can be checked without the game.

    Returns:
        ``(heights, material indices, material names)``.
    """
    data = Path(path).read_bytes()
    offset = 0

    (version,) = struct.unpack_from("<B", data, offset)
    offset += 1
    if version != TER_VERSION:
        raise TerrainFileError(f"unsupported .ter version {version}")

    (size,) = struct.unpack_from("<I", data, offset)
    offset += 4

    cells = size * size

    heights = np.frombuffer(data, dtype="<u2", count=cells, offset=offset).reshape(size, size)
    offset += cells * 2

    indices = np.frombuffer(data, dtype=np.uint8, count=cells, offset=offset).reshape(size, size)
    offset += cells

    (material_count,) = struct.unpack_from("<I", data, offset)
    offset += 4

    materials = []
    for _ in range(material_count):
        (length,) = struct.unpack_from("<B", data, offset)
        offset += 1
        materials.append(data[offset : offset + length].decode("ascii"))
        offset += length

    return heights.copy(), indices.copy(), materials

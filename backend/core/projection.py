"""
Projection from geographic coordinates into BeamNG world space.

BeamNG levels use a flat, metric, right-handed coordinate system: +X east,
+Y north, +Z up, in metres. The terrain block is centred on the origin, so a
level covering a 5 km region spans roughly -2500..+2500 on both axes.

Anything placed on the map - a road node, a building - has to be converted from
latitude/longitude into that space. The previous attempt did::

    x = lon * 111000
    y = lat * 111000
    z = 0.0

which is wrong three times over:

1. It produces *absolute* coordinates. San Francisco at -122.4 degrees becomes
   x = -13,586,400 - roughly 13,600 km from the level origin, far outside the
   terrain block and outside BeamNG's float precision comfort zone.
2. It uses the same metres-per-degree for longitude as for latitude. Longitude
   degrees shrink with the cosine of latitude; at 60 degrees north the error is
   a factor of two.
3. Every object sits at z = 0 regardless of the terrain underneath, so on a
   hilly map objects either float in the air or are buried.

:class:`LocalProjection` fixes all three: it is centred on the region, scales
longitude correctly, and samples elevation from the generated heightmap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.geo import METERS_PER_DEGREE_LAT, meters_per_degree_lon


@dataclass(frozen=True)
class LocalProjection:
    """
    Converts lat/lon to metres relative to the centre of a bounding box.

    Uses an equirectangular (plate carrée) projection evaluated at the region's
    centre latitude. For the tile sizes this app generates - single-digit
    kilometres - the distortion is well under a metre, far below the resolution
    of the underlying elevation data.
    """

    center_lat: float
    center_lon: float
    meters_per_deg_lat: float
    meters_per_deg_lon: float

    @classmethod
    def from_bbox(cls, bbox: list[float] | tuple[float, float, float, float]) -> LocalProjection:
        """Build a projection centred on ``[min_lon, min_lat, max_lon, max_lat]``."""
        min_lon, min_lat, max_lon, max_lat = bbox
        center_lat = (min_lat + max_lat) / 2.0
        center_lon = (min_lon + max_lon) / 2.0
        return cls(
            center_lat=center_lat,
            center_lon=center_lon,
            meters_per_deg_lat=METERS_PER_DEGREE_LAT,
            meters_per_deg_lon=meters_per_degree_lon(center_lat),
        )

    def to_world(self, lat: float, lon: float) -> tuple[float, float]:
        """
        Convert a geographic point to ``(x, y)`` metres in level space.

        Returns:
            ``x`` metres east of the region centre, ``y`` metres north of it.
        """
        x = (lon - self.center_lon) * self.meters_per_deg_lon
        y = (lat - self.center_lat) * self.meters_per_deg_lat
        return x, y

    def to_geographic(self, x: float, y: float) -> tuple[float, float]:
        """Inverse of :meth:`to_world`. Returns ``(lat, lon)``."""
        lat = self.center_lat + y / self.meters_per_deg_lat
        lon = self.center_lon + x / self.meters_per_deg_lon
        return lat, lon


class TerrainSampler:
    """
    Reads ground elevation at a world position.

    The heightmap is a normalised integer image; the real elevation is
    reconstructed with the same ``minHeight`` / ``heightScale`` pair that is
    written into ``main.level.json``, so a sampled Z always agrees with where
    the game will actually draw the ground.
    """

    def __init__(
        self,
        heightmap: np.ndarray,
        *,
        min_elevation: float,
        elevation_range: float,
        square_size: float,
    ) -> None:
        """
        Args:
            heightmap: Normalised heightmap, shape ``(size, size)``.
            min_elevation: Real-world elevation mapped to value 0.
            elevation_range: Real-world span covered by the full value range.
            square_size: Metres per heightmap pixel.
        """
        if heightmap.ndim != 2:
            raise ValueError(f"heightmap must be 2D, got shape {heightmap.shape}")

        self._heightmap = heightmap
        self._min_elevation = min_elevation
        self._elevation_range = elevation_range
        self._square_size = square_size

        self._rows, self._cols = heightmap.shape
        self._max_value = float(np.iinfo(heightmap.dtype).max) if heightmap.dtype.kind in "ui" else 1.0

        # The terrain block is centred on the origin, so world (0, 0) is the
        # middle of the image.
        self._half_width_m = self._cols * square_size / 2.0
        self._half_height_m = self._rows * square_size / 2.0

    def elevation_at(self, x: float, y: float) -> float:
        """
        Ground elevation in metres at world position ``(x, y)``.

        Positions outside the terrain are clamped to the nearest edge rather
        than raising: a road detected slightly outside the DEM footprint should
        still be placed at a sane height.
        """
        column = (x + self._half_width_m) / self._square_size
        # Image rows run north to south, so the Y axis is flipped.
        row = (self._half_height_m - y) / self._square_size

        column_index = int(np.clip(round(column), 0, self._cols - 1))
        row_index = int(np.clip(round(row), 0, self._rows - 1))

        normalised = float(self._heightmap[row_index, column_index]) / self._max_value
        return self._min_elevation + normalised * self._elevation_range

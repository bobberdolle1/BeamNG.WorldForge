"""
Geographic helpers.

The conversion between degrees and metres was duplicated (with slightly
different constants) in the Sentinel Hub client, the Azure Maps client and the
frontend. It lives here now so a fix applies everywhere.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: Metres per degree of latitude. Varies by ~1% between equator and pole; the
#: mean value is accurate enough for sizing a tile.
METERS_PER_DEGREE_LAT = 111_320.0


def meters_per_degree_lon(latitude: float) -> float:
    """Metres per degree of longitude at the given latitude."""
    return METERS_PER_DEGREE_LAT * math.cos(math.radians(latitude))


@dataclass(frozen=True)
class BBoxDimensions:
    """Physical size of a bounding box."""

    width_meters: float
    height_meters: float

    @property
    def area_km2(self) -> float:
        return (self.width_meters * self.height_meters) / 1_000_000

    @property
    def max_side_meters(self) -> float:
        return max(self.width_meters, self.height_meters)


def bbox_dimensions(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> BBoxDimensions:
    """
    Approximate the width and height of a bounding box in metres.

    Uses an equirectangular approximation evaluated at the box's centre
    latitude. Error is well under 1% for the tile sizes this app generates
    (single-digit kilometres).
    """
    center_lat = (min_lat + max_lat) / 2.0
    width = abs(max_lon - min_lon) * meters_per_degree_lon(center_lat)
    height = abs(max_lat - min_lat) * METERS_PER_DEGREE_LAT
    return BBoxDimensions(width_meters=width, height_meters=height)


def pixel_dimensions(
    bbox: list[float] | tuple[float, float, float, float],
    resolution_meters: float,
    *,
    min_size: int = 256,
    max_size: int = 2500,
) -> tuple[int, int]:
    """
    Convert a bbox plus a ground resolution into raster dimensions.

    Args:
        bbox: ``[min_lon, min_lat, max_lon, max_lat]``.
        resolution_meters: Desired ground sample distance.
        min_size: Lower clamp, so tiny requests still return a usable raster.
        max_size: Upper clamp, to stay inside provider request limits.

    Returns:
        ``(width, height)`` in pixels, aspect ratio preserved when clamping.
    """
    if resolution_meters <= 0:
        raise ValueError("resolution_meters must be positive")

    min_lon, min_lat, max_lon, max_lat = bbox
    dimensions = bbox_dimensions(min_lon, min_lat, max_lon, max_lat)

    width = max(int(dimensions.width_meters / resolution_meters), min_size)
    height = max(int(dimensions.height_meters / resolution_meters), min_size)

    if width > max_size or height > max_size:
        scale = min(max_size / width, max_size / height)
        width = max(int(width * scale), min_size)
        height = max(int(height * scale), min_size)

    return width, height

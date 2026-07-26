"""
AWS Terrain Tiles data source.

The one elevation source that needs no account, no key and no setup.

Every other provider the app supports requires registration before a single map
can be generated, which made "clone it and try it" impossible. AWS hosts the
Terrain Tiles dataset (originally Mapzen, now maintained as an AWS Open Data
registry set) as public, anonymous GeoTIFF tiles::

    https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif

The underlying data is a merge of SRTM, 3DEP, and several national datasets, so
resolution varies by region: roughly 30 m globally and 10 m over the continental
United States. Tiles are 512x512, int16 metres, in Web Mercator (EPSG:3857).

Attribution requirement: the dataset is a composite of public-domain and
CC-BY sources. See
https://github.com/tilezen/joerd/blob/master/docs/attribution.md
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import numpy as np
import requests

from core.logging_config import get_logger

from .base import (
    Capability,
    DataSourceError,
    DataSourceInterface,
)

logger = get_logger(__name__)

BASE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/geotiff"

#: Edge length of a tile in pixels.
TILE_SIZE = 512

#: Deepest zoom the dataset publishes.
MAX_ZOOM = 14

#: Cap on tiles per request. 64 tiles is a 4096x4096 mosaic - beyond that the
#: download dominates generation time for no visible gain, since the source
#: data is 30 m and would only be upsampled.
MAX_TILES = 64

_REQUEST_TIMEOUT = 30.0

#: Tiles over open ocean are absent; S3 answers 403 (not 404) for a missing key
#: under this bucket's policy, so both are treated as "no data here".
_MISSING_STATUSES = (403, 404)


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert a geographic point to slippy-map tile indices at ``zoom``."""
    # Clamp to the Web Mercator limit; the projection is undefined at the poles.
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2.0**zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return max(0, min(x, int(n) - 1)), max(0, min(y, int(n) - 1))


def tile_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
    """North-west corner of a tile, as ``(lat, lon)``."""
    n = 2.0**zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
    return lat, lon


def ground_resolution(lat: float, zoom: int) -> float:
    """Metres per pixel at a latitude and zoom, for 512 px tiles."""
    earth_circumference = 40_075_016.686
    return earth_circumference * math.cos(math.radians(lat)) / (2**zoom * TILE_SIZE)


def zoom_for_resolution(bbox: list[float], target_resolution: float) -> int:
    """
    Pick the shallowest zoom that meets ``target_resolution``, within limits.

    Deliberately conservative about going deeper: the source data tops out
    around 10 m, so a zoom beyond that returns interpolated pixels while
    multiplying the number of tiles to download by four each step.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lat = (min_lat + max_lat) / 2.0

    for zoom in range(1, MAX_ZOOM + 1):
        if ground_resolution(center_lat, zoom) <= target_resolution:
            return _clamp_zoom_to_tile_budget(bbox, zoom)

    return _clamp_zoom_to_tile_budget(bbox, MAX_ZOOM)


def _clamp_zoom_to_tile_budget(bbox: list[float], zoom: int) -> int:
    """Reduce zoom until the request fits inside :data:`MAX_TILES`."""
    min_lon, min_lat, max_lon, max_lat = bbox

    while zoom > 1:
        x_min, y_max = lat_lon_to_tile(min_lat, min_lon, zoom)
        x_max, y_min = lat_lon_to_tile(max_lat, max_lon, zoom)
        tiles = (abs(x_max - x_min) + 1) * (abs(y_max - y_min) + 1)
        if tiles <= MAX_TILES:
            return zoom
        zoom -= 1

    return 1


class AWSTerrainDataSource(DataSourceInterface):
    """Anonymous global elevation from the AWS Terrain Tiles dataset."""

    #: Elevation only; the dataset carries no imagery.
    capabilities = frozenset({Capability.DEM})

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.base_url = self.config.get("base_url", BASE_URL)
        self._session = requests.Session()

    # -- interface ------------------------------------------------------------

    def get_dem_data(self, bbox: list, resolution: int = 30) -> tuple[np.ndarray, dict]:
        """
        Fetch and mosaic elevation tiles covering ``bbox``.

        Args:
            bbox: ``[min_lon, min_lat, max_lon, max_lat]``.
            resolution: Desired ground resolution in metres.

        Returns:
            ``(elevation array in metres with NaN for voids, metadata)``.
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        zoom = zoom_for_resolution(bbox, resolution)

        x_min, y_max = lat_lon_to_tile(min_lat, min_lon, zoom)
        x_max, y_min = lat_lon_to_tile(max_lat, max_lon, zoom)

        coordinates = [
            (x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)
        ]

        actual_resolution = ground_resolution((min_lat + max_lat) / 2.0, zoom)
        logger.info(
            "Fetching %d AWS terrain tile(s) at zoom %d (~%.1f m/px)",
            len(coordinates),
            zoom,
            actual_resolution,
        )

        mosaic = self._download_mosaic(coordinates, zoom, x_min, y_min, x_max, y_max)
        cropped = self._crop_to_bbox(mosaic, bbox, zoom, x_min, y_min)

        if not np.isfinite(cropped).any():
            raise DataSourceError(
                "AWS Terrain Tiles has no elevation data for this region "
                "(it is most likely open ocean). Select an area over land."
            )

        metadata = {
            "bounds": bbox,
            "crs": "EPSG:4326",
            "width": cropped.shape[1],
            "height": cropped.shape[0],
            "resolution": round(actual_resolution, 2),
            "zoom": zoom,
            "tiles": len(coordinates),
            "source": "AWS Terrain Tiles (SRTM / 3DEP composite)",
        }

        logger.info(
            "Elevation mosaic ready: %dx%d, range %.1f..%.1f m",
            cropped.shape[1],
            cropped.shape[0],
            float(np.nanmin(cropped)),
            float(np.nanmax(cropped)),
        )
        return cropped, metadata

    def get_satellite_image(self, bbox: list, resolution: int = 10) -> tuple[np.ndarray, dict]:
        """Not available: the dataset is elevation only."""
        raise NotImplementedError(
            "AWS Terrain Tiles provides elevation only. Configure Sentinel Hub or "
            "Azure Maps for satellite imagery."
        )

    def test_connection(self) -> bool:
        """Check the bucket is reachable by requesting a single known tile."""
        try:
            response = self._session.head(f"{self.base_url}/0/0/0.tif", timeout=10.0)
            return response.status_code == 200
        except requests.RequestException as exc:
            logger.info("AWS Terrain Tiles unreachable: %s", exc)
            return False

    def requires_setup(self) -> bool:
        """No account, no key, nothing to configure."""
        return False

    def get_source_name(self) -> str:
        return "AWS Terrain Tiles"

    def get_source_description(self) -> str:
        return (
            "AWS Terrain Tiles - global elevation, no API key needed\n"
            "- ~30 m worldwide, ~10 m over the continental United States\n"
            "- Sources: SRTM, 3DEP, and national datasets\n"
            "- Elevation only, no satellite imagery\n"
            "- Works out of the box; no registration"
        )

    # -- internals ------------------------------------------------------------

    def _download_mosaic(
        self,
        coordinates: list[tuple[int, int]],
        zoom: int,
        x_min: int,
        y_min: int,
        x_max: int,
        y_max: int,
    ) -> np.ndarray:
        """Download tiles concurrently and assemble them into one array."""
        columns = x_max - x_min + 1
        rows = y_max - y_min + 1
        mosaic = np.full((rows * TILE_SIZE, columns * TILE_SIZE), np.nan, dtype=np.float32)

        # Tiles are independent GETs of ~150 KB; fetching them serially makes a
        # 16-tile region take 16 round trips. The pool is small because this
        # already runs inside a worker thread of a bounded pipeline.
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = pool.map(lambda coord: (coord, self._download_tile(*coord, zoom)), coordinates)

            missing = 0
            for (x, y), tile in results:
                if tile is None:
                    missing += 1
                    continue
                row_start = (y - y_min) * TILE_SIZE
                column_start = (x - x_min) * TILE_SIZE
                mosaic[row_start : row_start + TILE_SIZE, column_start : column_start + TILE_SIZE] = tile

        if missing:
            logger.info("%d of %d tiles had no data (ocean or gap)", missing, len(coordinates))

        return mosaic

    def _download_tile(self, x: int, y: int, zoom: int) -> np.ndarray | None:
        """Fetch one tile. Returns ``None`` when the tile does not exist."""
        url = f"{self.base_url}/{zoom}/{x}/{y}.tif"

        try:
            response = self._session.get(url, timeout=_REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise DataSourceError(f"Could not download terrain tile {zoom}/{x}/{y}: {exc}") from exc

        if response.status_code in _MISSING_STATUSES:
            return None
        if response.status_code != 200:
            raise DataSourceError(
                f"Terrain tile {zoom}/{x}/{y} returned HTTP {response.status_code}"
            )

        from rasterio.io import MemoryFile

        with MemoryFile(BytesIO(response.content)) as memfile, memfile.open() as reader:
            data = reader.read(1).astype(np.float32)
            nodata = reader.nodata

        if nodata is not None:
            data = np.where(data == nodata, np.nan, data)

        return data

    @staticmethod
    def _crop_to_bbox(
        mosaic: np.ndarray,
        bbox: list[float],
        zoom: int,
        x_min: int,
        y_min: int,
    ) -> np.ndarray:
        """
        Cut the requested region out of the tile mosaic.

        Tiles snap to a fixed grid, so the mosaic always covers more ground than
        was asked for. Without this crop the generated map would silently
        include a margin of up to one tile on every side - the terrain would not
        match the rectangle the user drew.
        """
        min_lon, min_lat, max_lon, max_lat = bbox

        def pixel_x(lon: float) -> float:
            n = 2.0**zoom
            tile_x = (lon + 180.0) / 360.0 * n
            return (tile_x - x_min) * TILE_SIZE

        def pixel_y(lat: float) -> float:
            lat = max(min(lat, 85.05112878), -85.05112878)
            n = 2.0**zoom
            tile_y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
            return (tile_y - y_min) * TILE_SIZE

        left = int(math.floor(pixel_x(min_lon)))
        right = int(math.ceil(pixel_x(max_lon)))
        top = int(math.floor(pixel_y(max_lat)))
        bottom = int(math.ceil(pixel_y(min_lat)))

        left = max(0, min(left, mosaic.shape[1] - 1))
        right = max(left + 1, min(right, mosaic.shape[1]))
        top = max(0, min(top, mosaic.shape[0] - 1))
        bottom = max(top + 1, min(bottom, mosaic.shape[0]))

        return mosaic[top:bottom, left:right]

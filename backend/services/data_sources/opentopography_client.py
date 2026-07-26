"""
OpenTopography data source implementation

Provides access to high-quality DEM data:
- SRTM (30m, 90m resolution)
- ASTER GDEM (30m resolution)
- ALOS World 3D (30m resolution)

Free access with optional API key for higher quotas
"""

import os

import numpy as np
import requests

from core.logging_config import get_logger

from .base import (
    Capability,
    DataSourceError,
    DataSourceInterface,
    DataSourceUnavailableError,
)

logger = get_logger(__name__)

#: Timeout for a DEM download. Large boxes are assembled server-side and can
#: legitimately take over a minute.
_REQUEST_TIMEOUT = 120.0

#: Timeout for the cheap availability probe.
_TEST_TIMEOUT = 20.0


class OpenTopographyDataSource(DataSourceInterface):
    """
    OpenTopography API client for DEM data
    
    A free API key is required for the global datasets:
    https://opentopography.org/
    """

    BASE_URL = "https://portal.opentopography.org/API/globaldem"

    #: Elevation only - OpenTopography does not serve imagery.
    capabilities = frozenset({Capability.DEM})
    
    # Available DEM datasets
    DATASETS = {
        'SRTMGL3': 'SRTM GL3 (90m)',
        'SRTMGL1': 'SRTM GL1 (30m)',
        'SRTMGL1_E': 'SRTM GL1 Ellipsoidal (30m)',
        'AW3D30': 'ALOS World 3D (30m)',
        'AW3D30_E': 'ALOS World 3D Ellipsoidal (30m)',
        'SRTM15Plus': 'SRTM15+ (500m, global)',
        'NASADEM': 'NASADEM (30m)',
        'COP30': 'Copernicus 30m',
        'COP90': 'Copernicus 90m'
    }
    
    def __init__(self, config: dict | None = None):
        super().__init__(config)

        self.api_key = self.config.get('api_key') or os.getenv('OPENTOPOGRAPHY_API_KEY')
        self.default_dataset = self.config.get('dataset') or 'SRTMGL1'

        #: Cached outcome of test_connection(). None means "not checked yet".
        self._connection_ok: bool | None = None


    def get_dem_data(
        self,
        bbox: list,
        resolution: int = 30
    ) -> tuple[np.ndarray, dict]:
        """
        Fetch DEM data from OpenTopography
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            resolution: Desired resolution in meters (will select best dataset)
        
        Returns:
            Tuple of (elevation array, metadata)
        """
        if not self.api_key:
            raise DataSourceUnavailableError(
                "OpenTopography requires a free API key. Get one at "
                "https://opentopography.org/ and add it in Settings."
            )

        min_lon, min_lat, max_lon, max_lat = bbox

        logger.info("Fetching DEM from OpenTopography for bbox %s at ~%sm", bbox, resolution)

        # Try the preferred dataset, then progressively coarser fallbacks.
        # Coverage is not uniform: COP30 has gaps above 60 deg N/S and SRTM
        # stops at 60 deg entirely, so a single hardcoded dataset returns an
        # error for large parts of the world.
        last_error: Exception | None = None
        for dataset in self._dataset_candidates(resolution):
            try:
                response = requests.get(
                    self.BASE_URL,
                    params={
                        'demtype': dataset,
                        'south': min_lat,
                        'north': max_lat,
                        'west': min_lon,
                        'east': max_lon,
                        'outputFormat': 'GTiff',
                        'API_Key': self.api_key,
                    },
                    timeout=_REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("Request for %s failed: %s", dataset, exc)
                continue

            if response.status_code in (401, 403):
                raise DataSourceUnavailableError(
                    "OpenTopography rejected the API key. Check it in Settings, or get a "
                    "free key at https://opentopography.org/"
                )

            if response.status_code == 429:
                raise DataSourceError(
                    "OpenTopography rate limit reached. Wait a minute and try again."
                )

            if response.status_code != 200:
                last_error = DataSourceError(
                    f"{dataset} returned HTTP {response.status_code}: {response.text[:200]}"
                )
                logger.warning("Dataset %s unavailable for this region, trying next", dataset)
                continue

            elevation_data, metadata = self._parse_geotiff(response.content, bbox, resolution, dataset)
            logger.info(
                "DEM fetched from %s: %sx%s, range %.1fm to %.1fm",
                self.DATASETS[dataset],
                elevation_data.shape[1],
                elevation_data.shape[0],
                float(np.nanmin(elevation_data)),
                float(np.nanmax(elevation_data)),
            )
            return elevation_data, metadata

        raise DataSourceError(
            f"No OpenTopography dataset covers this region. Last error: {last_error}"
        )

    def _parse_geotiff(
        self, content: bytes, bbox: list, resolution: int, dataset: str
    ) -> tuple[np.ndarray, dict]:
        """Decode a GeoTIFF response into a float array with NaN for nodata."""
        from rasterio.io import MemoryFile

        with MemoryFile(content) as memfile, memfile.open() as reader:
            elevation = reader.read(1).astype(np.float32)
            nodata = reader.nodata
            if nodata is not None:
                elevation = np.where(elevation == nodata, np.nan, elevation)

            metadata = {
                'bounds': bbox,
                'crs': str(reader.crs),
                'width': reader.width,
                'height': reader.height,
                'resolution': resolution,
                'transform': reader.transform,
                'nodata': nodata,
                'source': f'OpenTopography - {self.DATASETS[dataset]}',
            }

        return elevation, metadata

    def get_satellite_image(
        self,
        bbox: list,
        resolution: int = 10
    ) -> tuple[np.ndarray, dict]:
        """
        OpenTopography does not provide satellite imagery
        
        This method raises NotImplementedError. Use Sentinel Hub or GEE for imagery.
        """
        raise NotImplementedError(
            "OpenTopography only provides DEM data, not satellite imagery. "
            "Use Sentinel Hub or Google Earth Engine for satellite images."
        )
    
    def test_connection(self) -> bool:
        """
        Test OpenTopography connectivity.

        Since 2022 the global datasets require an API key, so a keyless client
        is unusable and we say so without spending a request. The check is also
        cached: ``is_available()`` is called for every source on every page
        load of the generation panel, and the old implementation downloaded a
        real DEM tile each time - slow, and it burned the user's quota just to
        render a dropdown.
        """
        if not self.api_key:
            logger.info(
                "OpenTopography needs a free API key (https://opentopography.org/). "
                "Add it in Settings to enable this source."
            )
            return False

        if self._connection_ok is not None:
            return self._connection_ok

        try:
            # Smallest possible request: a ~1 km box at 90 m resolution.
            response = requests.get(
                self.BASE_URL,
                params={
                    "demtype": "SRTMGL3",
                    "south": 37.77,
                    "north": 37.78,
                    "west": -122.42,
                    "east": -122.41,
                    "outputFormat": "GTiff",
                    "API_Key": self.api_key,
                },
                timeout=_TEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.info("OpenTopography connection test failed: %s", exc)
            return False

        if response.status_code == 200:
            self._connection_ok = True
            return True

        if response.status_code in (401, 403):
            logger.warning("OpenTopography rejected the API key (HTTP %s)", response.status_code)
        else:
            logger.warning("OpenTopography test returned HTTP %s", response.status_code)

        self._connection_ok = False
        return False

    def requires_setup(self) -> bool:
        """OpenTopography requires a free API key for the global datasets."""
        return True

    def get_source_name(self) -> str:
        return "OpenTopography"

    def get_source_description(self) -> str:
        return (
            "OpenTopography - High-quality global elevation data\n"
            "- Copernicus DEM (30m, 90m)\n"
            "- SRTM (30m, 90m)\n"
            "- ALOS World 3D (30m), NASADEM (30m)\n"
            "- Elevation only, no satellite imagery\n"
            "- Free API key required: https://opentopography.org/"
        )

    def _dataset_candidates(self, resolution: int) -> tuple[str, ...]:
        """
        Datasets to try, best first.

        Returning a sequence rather than a single dataset matters because
        coverage differs per product: SRTM stops at 60 degrees latitude and
        Copernicus has voids over some water bodies. If the preferred dataset
        has no data for the requested box, the caller falls through to the next
        one instead of failing the whole generation.
        """
        if resolution <= 30:
            return ('COP30', 'SRTMGL1', 'NASADEM', 'AW3D30', 'SRTMGL3')
        if resolution <= 90:
            return ('COP90', 'SRTMGL3', 'COP30')
        return ('SRTM15Plus', 'COP90', 'SRTMGL3')

    def _select_dataset(self, resolution: int) -> str:
        """Return the single best dataset for a resolution (first candidate)."""
        return self._dataset_candidates(resolution)[0]


    def set_dataset(self, dataset: str):
        """
        Manually set the DEM dataset to use
        
        Args:
            dataset: Dataset identifier (e.g., 'SRTMGL1', 'AW3D30')
        """
        if dataset not in self.DATASETS:
            raise ValueError(
                f"Unknown dataset: {dataset}. "
                f"Available: {', '.join(self.DATASETS.keys())}"
            )
        
        self.default_dataset = dataset
        print(f"📡 OpenTopography dataset set to: {self.DATASETS[dataset]}")

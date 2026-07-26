"""
Sentinel Hub data source implementation

Provides access to:
- Sentinel-2 satellite imagery (10m resolution, RGB)
- Copernicus DEM (30m resolution)

Free tier available with registration at https://www.sentinel-hub.com/
"""

import os
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import requests
from PIL import Image

from core.geo import pixel_dimensions
from core.logging_config import get_logger

from .base import Capability, DataSourceInterface

logger = get_logger(__name__)

#: Timeout for the OAuth token exchange - a small, fast request.
_AUTH_TIMEOUT = 30.0

#: Timeout for a Processing API call, which renders a raster server-side and
#: can legitimately take a minute for a large tile. Previously these calls had
#: no timeout at all, so a stalled connection hung the request forever.
_REQUEST_TIMEOUT = 180.0


class SentinelHubDataSource(DataSourceInterface):
    """
    Sentinel Hub API client for free satellite data access
    
    Authentication:
    - Requires OAuth2 client ID and secret
    - Get free account at: https://www.sentinel-hub.com/
    - Free tier: 30,000 processing units/month (sufficient for MVP)
    """
    
    BASE_URL = "https://services.sentinel-hub.com"

    #: Sentinel Hub serves both Copernicus DEM and Sentinel-2 imagery.
    capabilities = frozenset({Capability.DEM, Capability.IMAGERY})
    
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        
        # Get credentials from config or environment
        self.client_id = self.config.get('client_id') or os.getenv('SENTINEL_HUB_CLIENT_ID')
        self.client_secret = self.config.get('client_secret') or os.getenv('SENTINEL_HUB_CLIENT_SECRET')
        
        self._access_token = None
        self._token_expires = None
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token (cached)"""
        # Return cached token if still valid
        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return self._access_token
        
        # Request new token
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Sentinel Hub credentials not configured. "
                "Set SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET environment variables "
                "or provide in config dict."
            )
        
        url = f"{self.BASE_URL}/oauth/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(url, data=data, timeout=_AUTH_TIMEOUT)
        response.raise_for_status()
        
        token_data = response.json()
        self._access_token = token_data['access_token']
        expires_in = token_data['expires_in']  # seconds
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)  # 60s buffer
        
        return self._access_token
    
    def get_dem_data(
        self,
        bbox: list,
        resolution: int = 30
    ) -> tuple[np.ndarray, dict]:
        """
        Fetch DEM data from Copernicus DEM
        
        Uses Copernicus DEM GLO-30 (30m resolution)
        """
        logger.info("📡 Fetching DEM from Sentinel Hub (Copernicus DEM)...")
        logger.info(f"   BBox: {bbox}, Resolution: {resolution}m")
        
        token = self._get_access_token()
        
        # Calculate image size based on bbox and resolution
        min_lon, min_lat, max_lon, max_lat = bbox
        width, height = self._calculate_image_size(bbox, resolution)
        
        # Evalscript for DEM data
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: ["DEM"],
                output: {
                    bands: 1,
                    sampleType: "FLOAT32"
                }
            };
        }
        
        function evaluatePixel(sample) {
            return [sample.DEM];
        }
        """
        
        # API request
        url = f"{self.BASE_URL}/api/v1/process"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'image/tiff'
        }
        
        payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "DEM",
                    "dataFilter": {
                        "demInstance": "COPERNICUS_30"
                    }
                }]
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{
                    "identifier": "default",
                    "format": {"type": "image/tiff"}
                }]
            },
            "evalscript": evalscript
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Parse GeoTIFF response
        from rasterio.io import MemoryFile
        
        with MemoryFile(response.content) as memfile, memfile.open() as dataset:
            elevation_data = dataset.read(1)
            metadata = {
                'bounds': bbox,
                'crs': 'EPSG:4326',
                'width': width,
                'height': height,
                'resolution': resolution,
                'source': 'Sentinel Hub - Copernicus DEM GLO-30'
            }
        
        print(f"✅ DEM data fetched: {elevation_data.shape}, "
              f"range: [{np.nanmin(elevation_data):.1f}, {np.nanmax(elevation_data):.1f}]m")
        
        return elevation_data, metadata
    
    def get_satellite_image(
        self,
        bbox: list,
        resolution: int = 10
    ) -> tuple[np.ndarray, dict]:
        """
        Fetch RGB satellite image from Sentinel-2
        
        Uses Sentinel-2 L2A (atmospherically corrected)
        Resolution: 10m for RGB bands
        """
        logger.info("📡 Fetching satellite image from Sentinel Hub (Sentinel-2)...")
        
        token = self._get_access_token()
        
        # Calculate image size
        width, height = self._calculate_image_size(bbox, resolution)
        
        # Evalscript for true-color RGB
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["B04", "B03", "B02"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "AUTO"
                }
            };
        }
        
        function evaluatePixel(sample) {
            return [2.5 * sample.B04 / 10000, 2.5 * sample.B03 / 10000, 2.5 * sample.B02 / 10000];
        }
        """
        
        # Time range: last 6 months with cloud filter
        date_to = datetime.now().strftime('%Y-%m-%d')
        date_from = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/api/v1/process"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "S2L2A",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{date_from}T00:00:00Z",
                            "to": f"{date_to}T23:59:59Z"
                        },
                        "maxCloudCoverage": 20
                    }
                }]
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{
                    "identifier": "default",
                    "format": {"type": "image/png"}
                }]
            },
            "evalscript": evalscript
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Parse PNG response
        img = Image.open(BytesIO(response.content))
        rgb_data = np.array(img)
        
        # Ensure RGB format
        if rgb_data.ndim == 2:
            rgb_data = np.stack([rgb_data] * 3, axis=-1)
        elif rgb_data.shape[2] == 4:  # RGBA
            rgb_data = rgb_data[:, :, :3]
        
        metadata = {
            'bounds': bbox,
            'crs': 'EPSG:4326',
            'width': width,
            'height': height,
            'resolution': resolution,
            'source': 'Sentinel Hub - Sentinel-2 L2A'
        }
        
        logger.info(f"✅ Satellite image fetched: {rgb_data.shape}")
        
        return rgb_data, metadata
    
    def has_credentials(self) -> bool:
        """True if both halves of the OAuth2 client credential pair are set."""
        return bool(self.client_id and self.client_secret)

    def test_connection(self) -> bool:
        """
        Test Sentinel Hub connectivity.

        Returns False immediately when credentials are missing, so building the
        data source list does not make a doomed network round trip for every
        unconfigured provider.
        """
        if not self.has_credentials():
            return False
        try:
            return bool(self._get_access_token())
        except Exception as exc:  # noqa: BLE001 - reported through the return value
            logger.info("Sentinel Hub connection test failed: %s", exc)
            return False
    
    def requires_setup(self) -> bool:
        """Sentinel Hub requires free account registration"""
        return True
    
    def get_source_name(self) -> str:
        return "Sentinel Hub"
    
    def get_source_description(self) -> str:
        return (
            "Sentinel Hub - Free satellite data access\n"
            "- Sentinel-2 imagery (10m RGB)\n"
            "- Copernicus DEM (30m elevation)\n"
            "- Free tier: 30,000 processing units/month\n"
            "- Registration required: https://www.sentinel-hub.com/"
        )
    
    def _calculate_image_size(self, bbox: list, resolution: int) -> tuple[int, int]:
        """
        Calculate raster dimensions for a bbox at a given ground resolution.

        Clamped to 2500 px per side: Sentinel Hub's Processing API rejects
        larger requests, and an oversized tile burns processing units fast.
        """
        return pixel_dimensions(bbox, resolution, min_size=256, max_size=2500)

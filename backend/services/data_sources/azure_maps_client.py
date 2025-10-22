"""
Azure Maps data source implementation

Provides access to:
- High-resolution satellite imagery (aerial photos)
- Microsoft's replacement for Bing Maps
- Better quality and future-proof solution

Requires Azure Maps account and subscription key
"""

import os
import numpy as np
import requests
from typing import Tuple, Optional
from PIL import Image
from io import BytesIO
from math import pi, sin, cos, log, exp, atan

from .base import DataSourceInterface, DataSourceType


class AzureMapsDataSource(DataSourceInterface):
    """
    Azure Maps Rendering API client
    
    Microsoft's modern replacement for Bing Maps
    
    Authentication:
    - Requires Azure Maps subscription key
    - Get account at: https://azure.microsoft.com/en-us/products/azure-maps/
    - Free tier: S0 - 1,000 transactions/day, 5 requests/second
    """
    
    BASE_URL = "https://atlas.microsoft.com/map/tile"
    TILE_SIZE = 256  # Azure Maps uses 256x256 tiles
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        
        # Get subscription key from config or environment
        self.subscription_key = self.config.get('subscription_key') or os.getenv('AZURE_MAPS_SUBSCRIPTION_KEY')
    
    def get_dem_data(
        self,
        bbox: list,
        resolution: int = 30
    ) -> Tuple[np.ndarray, dict]:
        """
        Azure Maps does not provide DEM data
        
        This method raises NotImplementedError. Use OpenTopography or other sources for DEM.
        """
        raise NotImplementedError(
            "Azure Maps only provides satellite imagery, not DEM data. "
            "Use OpenTopography, Sentinel Hub, or Google Earth Engine for elevation data."
        )
    
    def get_satellite_image(
        self,
        bbox: list,
        resolution: int = 10
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch satellite imagery from Azure Maps
        
        Uses Azure Maps Render Service to download satellite tiles
        """
        if not self.subscription_key:
            raise ValueError(
                "Azure Maps subscription key is required. "
                "Set AZURE_MAPS_SUBSCRIPTION_KEY environment variable or provide in config. "
                "Get free account at: https://azure.microsoft.com/en-us/products/azure-maps/"
            )
        
        print(f"📡 Fetching satellite image from Azure Maps...")
        
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Calculate zoom level based on desired resolution
        zoom = self._calculate_zoom_level(bbox, resolution)
        print(f"   Using zoom level: {zoom}")
        
        # Get tile coordinates for the bounding box
        tiles = self._get_tiles_for_bbox(bbox, zoom)
        print(f"   Downloading {len(tiles)} tiles...")
        
        # Download and stitch tiles
        image = self._download_and_stitch_tiles(tiles, zoom)
        
        # Crop to exact bounding box
        image_cropped = self._crop_to_bbox(image, tiles, bbox, zoom)
        
        # Convert to numpy array
        rgb_data = np.array(image_cropped)
        
        # Ensure RGB format
        if rgb_data.ndim == 2:
            rgb_data = np.stack([rgb_data] * 3, axis=-1)
        elif rgb_data.shape[2] == 4:  # RGBA
            rgb_data = rgb_data[:, :, :3]
        
        metadata = {
            'bounds': bbox,
            'crs': 'EPSG:4326',
            'width': rgb_data.shape[1],
            'height': rgb_data.shape[0],
            'resolution': resolution,
            'zoom_level': zoom,
            'source': 'Azure Maps - Satellite Imagery'
        }
        
        print(f"✅ Satellite image fetched: {rgb_data.shape}")
        
        return rgb_data, metadata
    
    def test_connection(self) -> bool:
        """Test Azure Maps API connection"""
        if not self.subscription_key:
            print("⚠️  Azure Maps subscription key not configured")
            return False
        
        try:
            # Test with a single tile request (low quota impact)
            # Test tile: zoom 1, x=0, y=0 (small, always available)
            url = f"{self.BASE_URL}/png"
            params = {
                'api-version': '2.0',
                'tilesetId': 'microsoft.imagery',
                'zoom': 1,
                'x': 0,
                'y': 0,
                'subscription-key': self.subscription_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                print("✅ Azure Maps connection test passed")
                return True
            elif response.status_code == 401:
                print("⚠️  Azure Maps: Invalid subscription key")
                return False
            elif response.status_code == 403:
                print("⚠️  Azure Maps: Access forbidden (check subscription)")
                return False
            else:
                print(f"⚠️  Azure Maps test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Azure Maps connection test failed: {e}")
            return False
    
    def requires_setup(self) -> bool:
        """Azure Maps requires subscription key"""
        return True
    
    def get_source_name(self) -> str:
        return "Azure Maps"
    
    def get_source_description(self) -> str:
        return (
            "Azure Maps - Microsoft's modern mapping platform\n"
            "- High-quality satellite imagery\n"
            "- Replacement for Bing Maps (recommended by Microsoft)\n"
            "- Free tier: S0 - 1,000 transactions/day\n"
            "- Requires Azure account: https://azure.microsoft.com/en-us/products/azure-maps/\n\n"
            "⚠️  Note: Does not provide DEM data (use with OpenTopography/Sentinel Hub for terrain)"
        )
    
    def _lat_lon_to_tile_xy(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """
        Convert lat/lon to tile coordinates at given zoom level
        
        Uses Web Mercator projection (EPSG:3857)
        """
        lat_rad = lat * pi / 180.0
        n = 2.0 ** zoom
        
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int((1.0 - log(tan(lat_rad) + (1 / cos(lat_rad))) / pi) / 2.0 * n)
        
        return x_tile, y_tile
    
    def _tile_xy_to_lat_lon(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        """Convert tile coordinates to lat/lon"""
        n = 2.0 ** zoom
        
        lon = x / n * 360.0 - 180.0
        lat_rad = atan(sinh(pi * (1 - 2 * y / n)))
        lat = lat_rad * 180.0 / pi
        
        return lat, lon
    
    def _get_tiles_for_bbox(self, bbox: list, zoom: int) -> list:
        """Get list of tile coordinates covering the bounding box"""
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Get tile coordinates for corners
        x1, y1 = self._lat_lon_to_tile_xy(max_lat, min_lon, zoom)  # Top-left
        x2, y2 = self._lat_lon_to_tile_xy(min_lat, max_lon, zoom)  # Bottom-right
        
        # Generate list of all tiles
        tiles = []
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                tiles.append((x, y))
        
        return tiles
    
    def _download_tile(self, x: int, y: int, zoom: int) -> Image.Image:
        """Download a single tile from Azure Maps"""
        url = f"{self.BASE_URL}/png"
        
        params = {
            'api-version': '2.0',
            'tilesetId': 'microsoft.imagery',  # Satellite imagery tileset
            'zoom': zoom,
            'x': x,
            'y': y,
            'subscription-key': self.subscription_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        return Image.open(BytesIO(response.content))
    
    def _download_and_stitch_tiles(self, tiles: list, zoom: int) -> Image.Image:
        """Download and stitch multiple tiles into one image"""
        if not tiles:
            raise ValueError("No tiles to download")
        
        # Calculate grid dimensions
        xs = [t[0] for t in tiles]
        ys = [t[1] for t in tiles]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        grid_width = max_x - min_x + 1
        grid_height = max_y - min_y + 1
        
        # Create output image
        output_width = grid_width * self.TILE_SIZE
        output_height = grid_height * self.TILE_SIZE
        output_image = Image.new('RGB', (output_width, output_height))
        
        # Download and place tiles
        for x, y in tiles:
            try:
                tile_image = self._download_tile(x, y, zoom)
                
                # Calculate position in output image
                paste_x = (x - min_x) * self.TILE_SIZE
                paste_y = (y - min_y) * self.TILE_SIZE
                
                output_image.paste(tile_image, (paste_x, paste_y))
            except Exception as e:
                print(f"   ⚠️  Failed to download tile ({x}, {y}): {e}")
                # Continue with other tiles
        
        return output_image
    
    def _crop_to_bbox(
        self,
        image: Image.Image,
        tiles: list,
        bbox: list,
        zoom: int
    ) -> Image.Image:
        """Crop stitched image to exact bounding box"""
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Get tile grid bounds
        xs = [t[0] for t in tiles]
        ys = [t[1] for t in tiles]
        min_tile_x, max_tile_x = min(xs), max(xs)
        min_tile_y, max_tile_y = min(ys), max(ys)
        
        # Convert bbox to pixel coordinates within the stitched image
        def lon_to_pixel_x(lon):
            tile_x, _ = self._lat_lon_to_tile_xy(0, lon, zoom)
            return (tile_x - min_tile_x) * self.TILE_SIZE
        
        def lat_to_pixel_y(lat):
            _, tile_y = self._lat_lon_to_tile_xy(lat, 0, zoom)
            return (tile_y - min_tile_y) * self.TILE_SIZE
        
        # Calculate crop box
        left = int(lon_to_pixel_x(min_lon))
        top = int(lat_to_pixel_y(max_lat))
        right = int(lon_to_pixel_x(max_lon))
        bottom = int(lat_to_pixel_y(min_lat))
        
        # Ensure crop box is within image bounds
        left = max(0, left)
        top = max(0, top)
        right = min(image.width, right)
        bottom = min(image.height, bottom)
        
        return image.crop((left, top, right, bottom))
    
    def _calculate_zoom_level(self, bbox: list, target_resolution: int) -> int:
        """
        Calculate appropriate zoom level for target resolution
        
        Azure Maps zoom levels (similar to standard web maps):
        - Level 1: ~78 km/pixel
        - Level 10: ~152 m/pixel
        - Level 15: ~4.8 m/pixel
        - Level 20: ~0.15 m/pixel (max)
        """
        from math import cos, radians
        
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Center latitude for calculating meters per pixel
        center_lat = (min_lat + max_lat) / 2
        
        # Calculate bbox size in meters
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon
        
        # Earth circumference at equator
        earth_circumference = 40075017  # meters
        
        lat_meters = lat_diff * (earth_circumference / 360)
        lon_meters = lon_diff * (earth_circumference / 360) * cos(radians(center_lat))
        
        # Use larger dimension
        bbox_meters = max(lat_meters, lon_meters)
        
        # Calculate required pixels
        required_pixels = bbox_meters / target_resolution
        
        # Find appropriate zoom level
        for zoom in range(1, 21):  # Azure Maps supports up to zoom 20
            map_size_pixels = 256 * (2 ** zoom)
            pixels_per_degree = map_size_pixels / 360
            bbox_pixels = lon_diff * pixels_per_degree
            
            if bbox_pixels >= required_pixels * 0.8:  # 80% threshold
                return min(zoom, 20)  # Max zoom is 20
        
        return 20  # Default to max zoom


# Helper functions
def sinh(x):
    """Hyperbolic sine"""
    return (exp(x) - exp(-x)) / 2


def tan(x):
    """Tangent"""
    return sin(x) / cos(x)

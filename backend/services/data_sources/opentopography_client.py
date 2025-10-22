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
from typing import Tuple, Optional
from io import BytesIO

from .base import DataSourceInterface, DataSourceType


class OpenTopographyDataSource(DataSourceInterface):
    """
    OpenTopography API client for DEM data
    
    Free access available without API key (limited quota)
    Optional API key increases quota: https://opentopography.org/
    """
    
    BASE_URL = "https://portal.opentopography.org/API/globaldem"
    
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
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        
        # API key is optional but recommended
        self.api_key = self.config.get('api_key') or os.getenv('OPENTOPOGRAPHY_API_KEY')
        
        # Default dataset
        self.default_dataset = self.config.get('dataset', 'SRTMGL1')
    
    def get_dem_data(
        self,
        bbox: list,
        resolution: int = 30
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch DEM data from OpenTopography
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            resolution: Desired resolution in meters (will select best dataset)
        
        Returns:
            Tuple of (elevation array, metadata)
        """
        print(f"📡 Fetching DEM from OpenTopography...")
        print(f"   BBox: {bbox}, Resolution: ~{resolution}m")
        
        # Select best dataset based on resolution
        dataset = self._select_dataset(resolution)
        print(f"   Using dataset: {self.DATASETS[dataset]}")
        
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Build request parameters
        params = {
            'demtype': dataset,
            'south': min_lat,
            'north': max_lat,
            'west': min_lon,
            'east': max_lon,
            'outputFormat': 'GTiff'
        }
        
        # Add API key if available
        if self.api_key:
            params['API_Key'] = self.api_key
        
        # Make request
        response = requests.get(self.BASE_URL, params=params, timeout=120)
        
        if response.status_code == 401:
            raise RuntimeError(
                "OpenTopography API key required for this request. "
                "Get free key at: https://opentopography.org/blog/introducing-api-keys-access-opentopography-global-datasets"
            )
        
        response.raise_for_status()
        
        # Parse GeoTIFF
        from rasterio.io import MemoryFile
        
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset_reader:
                elevation_data = dataset_reader.read(1)
                
                # Handle nodata values
                nodata = dataset_reader.nodata
                if nodata is not None:
                    elevation_data = np.where(
                        elevation_data == nodata,
                        np.nan,
                        elevation_data
                    )
                
                metadata = {
                    'bounds': bbox,
                    'crs': str(dataset_reader.crs),
                    'width': dataset_reader.width,
                    'height': dataset_reader.height,
                    'resolution': resolution,
                    'transform': dataset_reader.transform,
                    'nodata': nodata,
                    'source': f'OpenTopography - {self.DATASETS[dataset]}'
                }
        
        print(f"✅ DEM data fetched: {elevation_data.shape}, "
              f"range: [{np.nanmin(elevation_data):.1f}, {np.nanmax(elevation_data):.1f}]m")
        
        return elevation_data, metadata
    
    def get_satellite_image(
        self,
        bbox: list,
        resolution: int = 10
    ) -> Tuple[np.ndarray, dict]:
        """
        OpenTopography does not provide satellite imagery
        
        This method raises NotImplementedError. Use Sentinel Hub or GEE for imagery.
        """
        raise NotImplementedError(
            "OpenTopography only provides DEM data, not satellite imagery. "
            "Use Sentinel Hub or Google Earth Engine for satellite images."
        )
    
    def test_connection(self) -> bool:
        """Test OpenTopography API connection"""
        try:
            # Test with small bbox around San Francisco
            test_bbox = [-122.42, 37.77, -122.41, 37.78]
            
            params = {
                'demtype': 'SRTMGL3',  # Use lower res for test
                'south': test_bbox[1],
                'north': test_bbox[3],
                'west': test_bbox[0],
                'east': test_bbox[2],
                'outputFormat': 'GTiff'
            }
            
            if self.api_key:
                params['API_Key'] = self.api_key
            
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            
            if response.status_code == 200:
                print("✅ OpenTopography connection test passed")
                return True
            elif response.status_code == 401:
                print("⚠️  OpenTopography requires API key (free registration)")
                return False
            else:
                print(f"⚠️  OpenTopography test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ OpenTopography connection test failed: {e}")
            return False
    
    def requires_setup(self) -> bool:
        """
        OpenTopography works without API key but has limited quota.
        API key recommended for production use.
        """
        return False  # Works without setup, but API key recommended
    
    def get_source_name(self) -> str:
        return "OpenTopography"
    
    def get_source_description(self) -> str:
        return (
            "OpenTopography - High-quality DEM data\n"
            "- SRTM (30m, 90m resolution)\n"
            "- ASTER GDEM (30m)\n"
            "- ALOS World 3D (30m)\n"
            "- Copernicus DEM (30m, 90m)\n"
            "- Free access (limited quota)\n"
            "- Optional API key for higher quota: https://opentopography.org/"
        )
    
    def _select_dataset(self, resolution: int) -> str:
        """
        Select best dataset based on desired resolution
        
        Args:
            resolution: Desired resolution in meters
        
        Returns:
            Dataset identifier
        """
        if resolution <= 30:
            # Best quality 30m datasets
            # Prefer COP30 (Copernicus) if available, otherwise SRTMGL1
            return 'COP30'  # Fallback to SRTMGL1 if COP30 fails
        elif resolution <= 90:
            return 'SRTMGL3'  # 90m
        else:
            return 'SRTM15Plus'  # 500m for very large areas
    
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

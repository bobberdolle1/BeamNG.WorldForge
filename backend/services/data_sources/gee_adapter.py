"""
Google Earth Engine adapter

Wraps the existing GEE client to conform to DataSourceInterface.
This is an OPTIONAL data source that requires manual setup.
"""

import numpy as np
from typing import Tuple, Optional
import os

from .base import DataSourceInterface, DataSourceType


class GEEDataSource(DataSourceInterface):
    """
    Google Earth Engine data source adapter
    
    OPTIONAL - Requires manual setup:
    1. Google Cloud account
    2. Earth Engine API enabled
    3. Service account JSON key
    
    This wraps the existing GEE client for backward compatibility.
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        
        self._gee_initialized = False
        self._gee_client = None
    
    def _ensure_initialized(self):
        """Initialize GEE client on first use"""
        if self._gee_initialized:
            return
        
        try:
            from services.gee.client import initialize_gee
            initialize_gee()
            self._gee_initialized = True
            print("✅ Google Earth Engine initialized")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Google Earth Engine: {e}\n\n"
                "GEE requires manual setup:\n"
                "1. Create Google Cloud account\n"
                "2. Enable Earth Engine API\n"
                "3. Create service account and download JSON key\n"
                "4. Set GEE_SERVICE_ACCOUNT_KEY environment variable\n"
                "5. Set GEE_PROJECT_ID environment variable\n\n"
                "See: https://developers.google.com/earth-engine/guides/service_account"
            )
    
    def get_dem_data(
        self,
        bbox: list,
        resolution: int = 30
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch DEM data from Google Earth Engine
        
        Uses the existing GEE client implementation.
        """
        self._ensure_initialized()
        
        from services.gee.client import get_dem_data
        
        print(f"📡 Fetching DEM from Google Earth Engine...")
        
        elevation_data, metadata = get_dem_data(
            bbox=bbox,
            resolution=resolution,
            dataset='USGS/SRTMGL1_003'
        )
        
        # Add source info to metadata
        metadata['source'] = 'Google Earth Engine - SRTM'
        
        return elevation_data, metadata
    
    def get_satellite_image(
        self,
        bbox: list,
        resolution: int = 10
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch satellite image from Google Earth Engine
        
        Uses the existing GEE client implementation.
        """
        self._ensure_initialized()
        
        from services.gee.client import get_satellite_image
        
        print(f"📡 Fetching satellite image from Google Earth Engine...")
        
        rgb_data, metadata = get_satellite_image(
            bbox=bbox,
            resolution=resolution,
            dataset='COPERNICUS/S2_SR'
        )
        
        # Add source info to metadata
        metadata['source'] = 'Google Earth Engine - Sentinel-2'
        
        return rgb_data, metadata
    
    def test_connection(self) -> bool:
        """Test GEE connection"""
        try:
            self._ensure_initialized()
            
            from services.gee.client import test_gee_connection
            return test_gee_connection()
            
        except Exception as e:
            print(f"❌ GEE connection test failed: {e}")
            return False
    
    def requires_setup(self) -> bool:
        """GEE requires extensive manual setup"""
        return True
    
    def get_source_name(self) -> str:
        return "Google Earth Engine"
    
    def get_source_description(self) -> str:
        return (
            "Google Earth Engine - Advanced satellite data platform\n"
            "- Sentinel-2, Landsat, MODIS imagery\n"
            "- SRTM, ASTER, NASA DEM\n"
            "- Massive archive dating back decades\n"
            "- Requires manual setup (Google Cloud account, API key)\n\n"
            "⚠️  OPTIONAL - Use only if you need advanced features\n"
            "Setup guide: https://developers.google.com/earth-engine/guides/service_account"
        )
    
    def is_available(self) -> bool:
        """Check if GEE is properly configured"""
        # Check for credentials
        key_path = os.getenv("GEE_SERVICE_ACCOUNT_KEY", "config/gee-key.json")
        project_id = os.getenv("GEE_PROJECT_ID")
        
        if not project_id:
            return False
        
        from pathlib import Path
        if not Path(key_path).exists():
            return False
        
        # Try to initialize
        try:
            self._ensure_initialized()
            return True
        except Exception:
            return False

"""
Base interface for data sources
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple, Optional
import numpy as np


class DataSourceType(str, Enum):
    """Available data source types"""
    SENTINEL_HUB = "sentinel_hub"
    OPENTOPOGRAPHY = "opentopography"
    BING_MAPS = "bing_maps"  # Deprecated - use AZURE_MAPS instead
    AZURE_MAPS = "azure_maps"
    GOOGLE_EARTH_ENGINE = "google_earth_engine"


class DataSourceInterface(ABC):
    """
    Abstract interface for geodata sources
    
    All data sources must implement these methods to provide
    DEM and satellite imagery in a unified format.
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize data source
        
        Args:
            config: Optional configuration dict (API keys, credentials, etc.)
        """
        self.config = config or {}
    
    @abstractmethod
    def get_dem_data(
        self,
        bbox: list,
        resolution: int = 30
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch Digital Elevation Model (DEM) data
        
        Args:
            bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]
            resolution: Resolution in meters
        
        Returns:
            Tuple of (elevation array [H, W], metadata dict)
            
        Metadata dict should contain:
            - bounds: Geographic bounds
            - crs: Coordinate reference system
            - width: Array width
            - height: Array height
            - resolution: Actual resolution in meters
        """
        pass
    
    @abstractmethod
    def get_satellite_image(
        self,
        bbox: list,
        resolution: int = 10
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch RGB satellite image
        
        Args:
            bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]
            resolution: Resolution in meters
        
        Returns:
            Tuple of (RGB array [H, W, 3], metadata dict)
            
        RGB array should be in range 0-255, uint8
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the data source is accessible
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def requires_setup(self) -> bool:
        """
        Check if this data source requires manual setup (API keys, etc.)
        
        Returns:
            True if manual setup is required, False if it works out-of-the-box
        """
        pass
    
    def get_source_name(self) -> str:
        """Get human-readable name of this data source"""
        return self.__class__.__name__
    
    def get_source_description(self) -> str:
        """Get description of this data source"""
        return "Data source for elevation and satellite imagery"
    
    def is_available(self) -> bool:
        """
        Check if this data source is available (credentials configured, API accessible)
        
        Returns:
            True if source is ready to use, False otherwise
        """
        try:
            return self.test_connection()
        except Exception as e:
            print(f"⚠️  {self.get_source_name()} is not available: {e}")
            return False


class DataSourceMetadata:
    """Metadata for data source responses"""
    
    def __init__(
        self,
        bounds: Tuple[float, float, float, float],
        crs: str,
        width: int,
        height: int,
        resolution: float,
        source_type: DataSourceType,
        additional: Optional[dict] = None
    ):
        self.bounds = bounds  # (min_lon, min_lat, max_lon, max_lat)
        self.crs = crs
        self.width = width
        self.height = height
        self.resolution = resolution
        self.source_type = source_type
        self.additional = additional or {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'bounds': self.bounds,
            'crs': self.crs,
            'width': self.width,
            'height': self.height,
            'resolution': self.resolution,
            'source_type': self.source_type.value,
            **self.additional
        }

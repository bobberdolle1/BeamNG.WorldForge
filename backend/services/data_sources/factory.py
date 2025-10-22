"""
Factory for creating data source instances
"""

from typing import Optional, Dict
from .base import DataSourceInterface, DataSourceType


class DataSourceFactory:
    """
    Factory for creating and managing data source instances
    """
    
    _instances: Dict[DataSourceType, DataSourceInterface] = {}
    
    @classmethod
    def create(
        cls,
        source_type: DataSourceType,
        config: Optional[dict] = None,
        force_recreate: bool = False
    ) -> DataSourceInterface:
        """
        Create or get a data source instance
        
        Args:
            source_type: Type of data source to create
            config: Optional configuration (API keys, etc.)
            force_recreate: Force recreation even if instance exists
        
        Returns:
            DataSourceInterface instance
        """
        # Return cached instance if exists and not forcing recreation
        if not force_recreate and source_type in cls._instances:
            return cls._instances[source_type]
        
        # Create new instance based on type
        if source_type == DataSourceType.SENTINEL_HUB:
            from .sentinel_hub_client import SentinelHubDataSource
            instance = SentinelHubDataSource(config)
        
        elif source_type == DataSourceType.OPENTOPOGRAPHY:
            from .opentopography_client import OpenTopographyDataSource
            instance = OpenTopographyDataSource(config)
        
        elif source_type == DataSourceType.BING_MAPS:
            from .bing_maps_client import BingMapsDataSource
            instance = BingMapsDataSource(config)
        
        elif source_type == DataSourceType.AZURE_MAPS:
            from .azure_maps_client import AzureMapsDataSource
            instance = AzureMapsDataSource(config)
        
        elif source_type == DataSourceType.GOOGLE_EARTH_ENGINE:
            from .gee_adapter import GEEDataSource
            instance = GEEDataSource(config)
        
        else:
            raise ValueError(f"Unknown data source type: {source_type}")
        
        # Cache instance
        cls._instances[source_type] = instance
        
        return instance
    
    @classmethod
    def get_default_source(cls) -> DataSourceInterface:
        """
        Get the default data source (Sentinel Hub + OpenTopography)
        
        Returns:
            Default data source instance
        """
        # Try Sentinel Hub first (best free option for satellite imagery)
        try:
            sentinel = cls.create(DataSourceType.SENTINEL_HUB)
            if sentinel.is_available():
                print("✅ Using Sentinel Hub as default data source")
                return sentinel
        except Exception as e:
            print(f"⚠️  Sentinel Hub not available: {e}")
        
        # Fallback to OpenTopography (DEM only)
        try:
            opentopo = cls.create(DataSourceType.OPENTOPOGRAPHY)
            if opentopo.is_available():
                print("✅ Using OpenTopography as default data source")
                return opentopo
        except Exception as e:
            print(f"⚠️  OpenTopography not available: {e}")
        
        # Last resort: try GEE if configured
        try:
            gee = cls.create(DataSourceType.GOOGLE_EARTH_ENGINE)
            if gee.is_available():
                print("✅ Using Google Earth Engine as fallback data source")
                return gee
        except Exception as e:
            print(f"⚠️  Google Earth Engine not available: {e}")
        
        raise RuntimeError(
            "No data sources available. Please configure at least one:\n"
            "- Sentinel Hub (recommended, free)\n"
            "- OpenTopography (free, DEM only)\n"
            "- Google Earth Engine (requires setup)"
        )
    
    @classmethod
    def get_available_sources(cls) -> list[DataSourceType]:
        """
        Get list of available data sources
        
        Returns:
            List of DataSourceType that are currently available
        """
        available = []
        
        for source_type in DataSourceType:
            try:
                source = cls.create(source_type)
                if source.is_available():
                    available.append(source_type)
            except Exception:
                pass
        
        return available
    
    @classmethod
    def clear_cache(cls):
        """Clear cached instances"""
        cls._instances.clear()

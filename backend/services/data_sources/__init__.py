"""
Data source abstraction layer for BeamNG.WorldForge

Provides unified interface for multiple geodata sources:
- Sentinel Hub (free, default)
- OpenTopography (free, default)
- Google Earth Engine (optional, requires setup)
"""

from .base import DataSourceInterface, DataSourceType
from .factory import DataSourceFactory

__all__ = [
    'DataSourceInterface',
    'DataSourceType',
    'DataSourceFactory'
]

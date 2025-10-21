"""Data models for the API"""
from .map_request import MapGenerationRequest, MapGenerationResponse, BoundingBox
from .terrain import TerrainData, HeightmapConfig

__all__ = [
    "MapGenerationRequest",
    "MapGenerationResponse",
    "BoundingBox",
    "TerrainData",
    "HeightmapConfig",
]


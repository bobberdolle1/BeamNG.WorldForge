"""Data models for the API"""
from .map_request import BoundingBox, MapGenerationRequest, MapGenerationResponse
from .terrain import HeightmapConfig, TerrainData

__all__ = [
    "MapGenerationRequest",
    "MapGenerationResponse",
    "BoundingBox",
    "TerrainData",
    "HeightmapConfig",
]


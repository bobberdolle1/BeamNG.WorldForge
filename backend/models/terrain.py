"""Models for terrain data"""

from pydantic import BaseModel, Field
from typing import Optional
import numpy as np


class HeightmapConfig(BaseModel):
    """Configuration for heightmap generation"""
    size: int = Field(1024, description="Heightmap size (width and height)")
    bit_depth: int = Field(16, description="Bit depth (8 or 16)")
    vertical_scale: float = Field(1.0, description="Vertical scale multiplier")
    interpolation: str = Field("bilinear", description="Interpolation method")
    
    class Config:
        arbitrary_types_allowed = True


class TerrainData(BaseModel):
    """Container for terrain elevation data"""
    elevation: list = Field(..., description="2D array of elevation values")
    min_elevation: float = Field(..., description="Minimum elevation in meters")
    max_elevation: float = Field(..., description="Maximum elevation in meters")
    width: int = Field(..., description="Width of the elevation grid")
    height: int = Field(..., description="Height of the elevation grid")
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def from_numpy(cls, data: np.ndarray):
        """Create TerrainData from numpy array"""
        return cls(
            elevation=data.tolist(),
            min_elevation=float(np.min(data)),
            max_elevation=float(np.max(data)),
            width=data.shape[1],
            height=data.shape[0]
        )
    
    def to_numpy(self) -> np.ndarray:
        """Convert elevation data back to numpy array"""
        return np.array(self.elevation, dtype=np.float32)


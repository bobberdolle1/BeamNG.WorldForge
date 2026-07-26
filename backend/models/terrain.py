"""Models for terrain data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator

Interpolation = Literal["nearest", "bilinear", "bicubic"]


class HeightmapConfig(BaseModel):
    """Configuration for heightmap generation."""

    size: int = Field(1024, ge=64, le=8192, description="Heightmap size (width and height)")
    bit_depth: Literal[8, 16] = Field(16, description="Bit depth of the output PNG")
    vertical_scale: float = Field(1.0, gt=0, description="Vertical exaggeration multiplier")
    interpolation: Interpolation = Field("bilinear", description="Resampling method")

    @field_validator("size")
    @classmethod
    def _power_of_two(cls, value: int) -> int:
        """
        BeamNG terrain blocks are square and power-of-two sized.

        A non-power-of-two heightmap loads but renders with a seam at the edge,
        so reject it here rather than shipping a broken mod.
        """
        if value & (value - 1) != 0:
            raise ValueError(f"heightmap size must be a power of two, got {value}")
        return value


@dataclass
class TerrainData:
    """
    Container for terrain elevation data.

    Holds the elevation grid as a numpy array. The previous version stored it
    as ``list[list[float]]`` inside a pydantic model, which meant a 2048x2048
    DEM was converted into ~4.2 million Python floats and validated element by
    element on every construction - hundreds of megabytes of RAM and several
    seconds of CPU for data that was immediately converted back to numpy.
    """

    elevation: np.ndarray
    #: Fraction of the grid that had no valid measurement in the source DEM.
    nodata_fraction: float = 0.0

    def __post_init__(self) -> None:
        array = np.asarray(self.elevation, dtype=np.float32)
        if array.ndim != 2:
            raise ValueError(f"elevation must be a 2D array, got shape {array.shape}")
        if array.size == 0:
            raise ValueError("elevation array is empty")
        self.elevation = array

    @property
    def height(self) -> int:
        return int(self.elevation.shape[0])

    @property
    def width(self) -> int:
        return int(self.elevation.shape[1])

    @property
    def min_elevation(self) -> float:
        return float(np.nanmin(self.elevation))

    @property
    def max_elevation(self) -> float:
        return float(np.nanmax(self.elevation))

    @property
    def elevation_range(self) -> float:
        return self.max_elevation - self.min_elevation

    @classmethod
    def from_numpy(cls, data: np.ndarray, nodata_fraction: float = 0.0) -> TerrainData:
        """Create TerrainData from a numpy array."""
        return cls(elevation=data, nodata_fraction=nodata_fraction)

    def to_numpy(self) -> np.ndarray:
        """Return the elevation grid as a float32 numpy array."""
        return self.elevation

    def summary(self) -> dict[str, float | int]:
        """Lightweight description suitable for logging or an API response."""
        return {
            "width": self.width,
            "height": self.height,
            "min_elevation": round(self.min_elevation, 2),
            "max_elevation": round(self.max_elevation, 2),
            "elevation_range": round(self.elevation_range, 2),
            "nodata_fraction": round(self.nodata_fraction, 4),
        }

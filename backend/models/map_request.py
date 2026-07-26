"""Models for map generation requests and responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from core.geo import bbox_dimensions
from core.paths import MAP_NAME_HELP, is_valid_map_name, slugify_map_name

#: Upper bound on the area a single request may cover.
#:
#: This is not arbitrary: at 30 m resolution a 400 km2 box is already ~22k x
#: 22k samples before resampling, which exhausts provider request limits and
#: makes generation take tens of minutes. Rejecting it up front gives the user
#: an actionable message instead of a timeout ten minutes in.
MAX_AREA_KM2 = 400.0

#: Below this the resulting terrain is a handful of DEM samples and looks flat.
MIN_AREA_KM2 = 0.01

DataSourceId = Literal[
    "auto",
    "aws_terrain",
    "sentinel_hub",
    "opentopography",
    "bing_maps",
    "azure_maps",
    "google_earth_engine",
]


class BoundingBox(BaseModel):
    """Geographic bounding box for the map region."""

    min_lat: float = Field(..., description="Minimum latitude", ge=-90, le=90)
    max_lat: float = Field(..., description="Maximum latitude", ge=-90, le=90)
    min_lon: float = Field(..., description="Minimum longitude", ge=-180, le=180)
    max_lon: float = Field(..., description="Maximum longitude", ge=-180, le=180)

    @model_validator(mode="after")
    def _validate_extent(self) -> BoundingBox:
        """
        Reject degenerate and oversized boxes.

        Previously any pair of in-range coordinates was accepted, so an
        inverted box (min > max) reached the data source, which returned an
        empty raster and produced a cryptic failure late in the pipeline.
        """
        if self.min_lat >= self.max_lat:
            raise ValueError("min_lat must be less than max_lat")
        if self.min_lon >= self.max_lon:
            raise ValueError("min_lon must be less than max_lon")

        area = self.area_km2
        if area < MIN_AREA_KM2:
            raise ValueError(
                f"Selected area is too small ({area:.4f} km2). Select at least {MIN_AREA_KM2} km2."
            )
        if area > MAX_AREA_KM2:
            raise ValueError(
                f"Selected area is too large ({area:.1f} km2). "
                f"The maximum is {MAX_AREA_KM2:.0f} km2 - select a smaller region."
            )
        return self

    @property
    def area_km2(self) -> float:
        """Approximate area of the box in square kilometres."""
        return bbox_dimensions(self.min_lon, self.min_lat, self.max_lon, self.max_lat).area_km2

    def to_list(self) -> list[float]:
        """Return ``[min_lon, min_lat, max_lon, max_lat]`` (the GDAL/EE order)."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]

    def to_ee_geometry(self) -> list[float]:
        """Alias of :meth:`to_list`, kept for backward compatibility."""
        return self.to_list()


class MapGenerationRequest(BaseModel):
    """Request to generate a BeamNG map."""

    name: str = Field(..., description="Name for the generated map", min_length=3, max_length=80)
    bbox: BoundingBox = Field(..., description="Geographic bounding box")
    resolution: int = Field(30, description="DEM resolution in metres", ge=10, le=500)
    heightmap_size: int = Field(
        1024, description="Heightmap texture size (power of two)", ge=256, le=4096
    )
    data_source: DataSourceId = Field(
        "auto",
        description="Data source to use; 'auto' picks the best configured source",
    )
    use_ai_segmentation: bool = Field(
        False,
        description="Run AI segmentation over satellite imagery (requires Ollama and an imagery source)",
    )

    @field_validator("name", mode="after")
    @classmethod
    def _normalise_name(cls, value: str) -> str:
        """
        Normalise the map name to a filesystem-safe slug.

        The name becomes a directory inside the mod archive and the archive's
        own filename. Accepting it unchecked allowed path traversal
        (``../../config/settings.key``); slugifying closes that off while still
        accepting friendly input like ``"San Francisco Downtown"``.
        """
        slug = slugify_map_name(value)
        if not is_valid_map_name(slug):
            raise ValueError(MAP_NAME_HELP)
        return slug

    @field_validator("heightmap_size", mode="after")
    @classmethod
    def _power_of_two(cls, value: int) -> int:
        """BeamNG terrain blocks must be power-of-two sized."""
        if value & (value - 1) != 0:
            raise ValueError(f"heightmap_size must be a power of two (512, 1024, 2048, 4096), got {value}")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "san_francisco_downtown",
                "bbox": {
                    "min_lat": 37.7749,
                    "max_lat": 37.8049,
                    "min_lon": -122.4294,
                    "max_lon": -122.3994,
                },
                "resolution": 30,
                "heightmap_size": 1024,
                "data_source": "auto",
                "use_ai_segmentation": False,
            }
        }
    }


class MapGenerationResponse(BaseModel):
    """Response returned when a generation job is accepted."""

    success: bool
    message: str
    map_id: str | None = None
    map_name: str | None = None
    download_url: str | None = None
    preview_url: str | None = None
    error: str | None = None


class JobStatusResponse(BaseModel):
    """Current state of a generation job."""

    job_id: str
    status: str
    progress: int
    message: str
    map_name: str | None = None
    error: str | None = None
    download_url: str | None = None
    preview_url: str | None = None
    stats: dict[str, Any] | None = None
    created_at: float | None = None
    updated_at: float | None = None

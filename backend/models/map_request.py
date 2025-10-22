"""Models for map generation requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class BoundingBox(BaseModel):
    """Geographic bounding box for the map region"""
    min_lat: float = Field(..., description="Minimum latitude", ge=-90, le=90)
    max_lat: float = Field(..., description="Maximum latitude", ge=-90, le=90)
    min_lon: float = Field(..., description="Minimum longitude", ge=-180, le=180)
    max_lon: float = Field(..., description="Maximum longitude", ge=-180, le=180)
    
    def to_ee_geometry(self):
        """Convert to Earth Engine geometry format"""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


class MapGenerationRequest(BaseModel):
    """Request to generate a BeamNG map"""
    name: str = Field(..., description="Name for the generated map", min_length=3, max_length=50)
    bbox: BoundingBox = Field(..., description="Geographic bounding box")
    resolution: Optional[int] = Field(30, description="DEM resolution in meters", ge=10, le=100)
    heightmap_size: Optional[int] = Field(1024, description="Heightmap texture size (power of 2)", ge=512, le=4096)
    data_source: Optional[Literal["auto", "sentinel_hub", "opentopography", "google_earth_engine"]] = Field(
        "auto",
        description="Data source to use (auto=best available, sentinel_hub=free, opentopography=free DEM only, google_earth_engine=requires setup)"
    )
    use_ai_segmentation: Optional[bool] = Field(False, description="Enable AI-powered image segmentation (Etап 2)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "san_francisco_downtown",
                "bbox": {
                    "min_lat": 37.7749,
                    "max_lat": 37.8049,
                    "min_lon": -122.4294,
                    "max_lon": -122.3994
                },
                "resolution": 30,
                "heightmap_size": 1024,
                "data_source": "auto",
                "use_ai_segmentation": True
            }
        }


class MapGenerationResponse(BaseModel):
    """Response from map generation"""
    success: bool
    message: str
    map_id: Optional[str] = None
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None


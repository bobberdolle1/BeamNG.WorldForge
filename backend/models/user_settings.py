"""User settings model for API keys and preferences"""

from pydantic import BaseModel, Field
from typing import Optional


class APIKeys(BaseModel):
    """API keys for external services"""
    sentinel_hub_client_id: Optional[str] = Field(None, description="Sentinel Hub Client ID")
    sentinel_hub_client_secret: Optional[str] = Field(None, description="Sentinel Hub Client Secret")
    opentopography_api_key: Optional[str] = Field(None, description="OpenTopography API Key")
    azure_maps_subscription_key: Optional[str] = Field(None, description="Azure Maps Subscription Key")
    bing_maps_api_key: Optional[str] = Field(None, description="Bing Maps API Key (deprecated)")
    gee_project_id: Optional[str] = Field(None, description="Google Earth Engine Project ID")


class UserPreferences(BaseModel):
    """User preferences for map generation"""
    default_data_source: str = Field("opentopography", description="Default data source for map generation")
    default_image_source: str = Field("sentinel_hub", description="Default imagery source")
    language: str = Field("en", description="UI language (en, ru)")


class UserSettings(BaseModel):
    """Complete user settings including API keys and preferences"""
    api_keys: APIKeys = Field(default_factory=APIKeys, description="API keys for external services")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")
    
    class Config:
        json_schema_extra = {
            "example": {
                "api_keys": {
                    "sentinel_hub_client_id": "your-client-id",
                    "sentinel_hub_client_secret": "your-client-secret",
                    "opentopography_api_key": "your-api-key",
                    "azure_maps_subscription_key": "your-subscription-key",
                    "gee_project_id": "your-project-id"
                },
                "preferences": {
                    "default_data_source": "opentopography",
                    "default_image_source": "azure_maps",
                    "language": "en"
                }
            }
        }


class SettingsUpdate(BaseModel):
    """Model for partial settings updates"""
    api_keys: Optional[APIKeys] = None
    preferences: Optional[UserPreferences] = None

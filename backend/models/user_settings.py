"""User settings model for API keys and preferences"""


from pydantic import BaseModel, Field


class APIKeys(BaseModel):
    """API keys for external services"""
    sentinel_hub_client_id: str | None = Field(None, description="Sentinel Hub Client ID")
    sentinel_hub_client_secret: str | None = Field(None, description="Sentinel Hub Client Secret")
    opentopography_api_key: str | None = Field(None, description="OpenTopography API Key")
    azure_maps_subscription_key: str | None = Field(None, description="Azure Maps Subscription Key")
    bing_maps_api_key: str | None = Field(None, description="Bing Maps API Key (deprecated)")
    gee_project_id: str | None = Field(None, description="Google Earth Engine Project ID")


class UserPreferences(BaseModel):
    """User preferences for map generation"""
    default_data_source: str = Field("opentopography", description="Default data source for map generation")
    default_image_source: str = Field("sentinel_hub", description="Default imagery source")
    language: str = Field("en", description="UI language (en, ru)")


class UserSettings(BaseModel):
    """Complete user settings including API keys and preferences"""
    api_keys: APIKeys = Field(default_factory=APIKeys, description="API keys for external services")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User preferences")

    model_config = {
        "json_schema_extra": {
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
    }


class SettingsUpdate(BaseModel):
    """Model for partial settings updates"""
    api_keys: APIKeys | None = None
    preferences: UserPreferences | None = None


class CredentialValidationRequest(BaseModel):
    """
    Credentials submitted for a live validation check.

    Secrets travel in the request *body*, never the query string: query strings
    end up in server access logs, browser history and proxy logs, so the
    previous ``POST /validate/{service}?api_key=...`` design leaked every key a
    user tested.
    """

    api_key: str = Field(..., min_length=1, description="API key or client ID to validate")
    api_secret: str | None = Field(
        None,
        description="Client secret, for services that use OAuth2 client credentials (Sentinel Hub)",
    )


class CredentialValidationResult(BaseModel):
    """Outcome of a credential validation attempt."""

    valid: bool
    message: str | None = None
    error: str | None = None

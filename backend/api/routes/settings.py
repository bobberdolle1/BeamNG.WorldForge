"""API routes for user settings management"""

from fastapi import APIRouter, HTTPException, status
from models.user_settings import UserSettings, SettingsUpdate, APIKeys
from services.settings_manager import settings_manager
from typing import Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/", response_model=UserSettings)
async def get_settings():
    """Get current user settings (API keys are masked for security)"""
    try:
        settings = settings_manager.load_settings()
        
        # Mask sensitive API keys in response
        masked_settings = settings.model_copy(deep=True)
        if masked_settings.api_keys.sentinel_hub_client_secret:
            masked_settings.api_keys.sentinel_hub_client_secret = "***" + masked_settings.api_keys.sentinel_hub_client_secret[-4:]
        if masked_settings.api_keys.opentopography_api_key:
            masked_settings.api_keys.opentopography_api_key = "***" + masked_settings.api_keys.opentopography_api_key[-4:]
        if masked_settings.api_keys.azure_maps_subscription_key:
            masked_settings.api_keys.azure_maps_subscription_key = "***" + masked_settings.api_keys.azure_maps_subscription_key[-4:]
        if masked_settings.api_keys.bing_maps_api_key:
            masked_settings.api_keys.bing_maps_api_key = "***" + masked_settings.api_keys.bing_maps_api_key[-4:]
        
        return masked_settings
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")


@router.put("/", response_model=UserSettings)
async def update_settings(updates: SettingsUpdate):
    """Update user settings"""
    try:
        # Convert to dict for update
        updates_dict = updates.model_dump(exclude_none=True)
        updated_settings = settings_manager.update_settings(updates_dict)
        
        # Mask sensitive data in response
        masked_settings = updated_settings.model_copy(deep=True)
        if masked_settings.api_keys.sentinel_hub_client_secret:
            masked_settings.api_keys.sentinel_hub_client_secret = "***" + masked_settings.api_keys.sentinel_hub_client_secret[-4:]
        
        return masked_settings
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.post("/validate/{service}")
async def validate_api_key(service: str, api_key: str) -> Dict[str, Any]:
    """
    Validate an API key by making a test request
    
    Supported services:
    - sentinel_hub
    - opentopography
    - azure_maps
    - bing_maps
    """
    try:
        if service == "sentinel_hub":
            return await _validate_sentinel_hub(api_key)
        elif service == "opentopography":
            return await _validate_opentopography(api_key)
        elif service == "azure_maps":
            return await _validate_azure_maps(api_key)
        elif service == "bing_maps":
            return await _validate_bing_maps(api_key)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating {service} key: {e}")
        return {"valid": False, "error": str(e)}


async def _validate_sentinel_hub(client_id: str) -> Dict[str, Any]:
    """Validate Sentinel Hub credentials"""
    try:
        # Test with a simple configuration request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://services.sentinel-hub.com/configuration/v1/datasets",
                headers={"Authorization": f"Bearer {client_id}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                return {"valid": True, "message": "Sentinel Hub credentials valid"}
            elif response.status_code == 401:
                return {"valid": False, "error": "Invalid credentials"}
            else:
                return {"valid": False, "error": f"Unexpected response: {response.status_code}"}
    except Exception as e:
        return {"valid": False, "error": f"Connection error: {str(e)}"}


async def _validate_opentopography(api_key: str) -> Dict[str, Any]:
    """Validate OpenTopography API key"""
    try:
        # Test with a simple API info request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://portal.opentopography.org/API/globaldem",
                params={
                    "demtype": "SRTMGL1",
                    "south": 37.0,
                    "north": 37.1,
                    "west": -119.6,
                    "east": -119.5,
                    "outputFormat": "GTiff",
                    "API_Key": api_key
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return {"valid": True, "message": "OpenTopography API key valid"}
            elif response.status_code == 401 or response.status_code == 403:
                return {"valid": False, "error": "Invalid API key"}
            else:
                return {"valid": False, "error": f"Unexpected response: {response.status_code}"}
    except Exception as e:
        return {"valid": False, "error": f"Connection error: {str(e)}"}


async def _validate_azure_maps(subscription_key: str) -> Dict[str, Any]:
    """Validate Azure Maps subscription key"""
    try:
        # Test with a simple render request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://atlas.microsoft.com/map/tile",
                params={
                    "api-version": "2.0",
                    "tilesetId": "microsoft.imagery",
                    "zoom": 1,
                    "x": 0,
                    "y": 0,
                    "subscription-key": subscription_key
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return {"valid": True, "message": "Azure Maps subscription key valid"}
            elif response.status_code == 401 or response.status_code == 403:
                return {"valid": False, "error": "Invalid subscription key"}
            else:
                return {"valid": False, "error": f"Unexpected response: {response.status_code}"}
    except Exception as e:
        return {"valid": False, "error": f"Connection error: {str(e)}"}


async def _validate_bing_maps(api_key: str) -> Dict[str, Any]:
    """Validate Bing Maps API key"""
    try:
        # Test with metadata request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://dev.virtualearth.net/REST/v1/Imagery/Metadata/Aerial",
                params={
                    "key": api_key,
                    "o": "json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("statusCode") == 200:
                    return {"valid": True, "message": "Bing Maps API key valid (deprecated)"}
                else:
                    return {"valid": False, "error": "Invalid API key"}
            else:
                return {"valid": False, "error": f"Unexpected response: {response.status_code}"}
    except Exception as e:
        return {"valid": False, "error": f"Connection error: {str(e)}"}


@router.get("/defaults")
async def get_defaults():
    """Get default settings recommendations"""
    return {
        "recommended_data_source": "opentopography",
        "recommended_image_source": "azure_maps",
        "supported_languages": ["en", "ru"],
        "data_sources": [
            {
                "id": "opentopography",
                "name": "OpenTopography",
                "requires_key": True,
                "free_tier": True
            },
            {
                "id": "sentinel_hub",
                "name": "Sentinel Hub",
                "requires_key": True,
                "free_tier": True
            },
            {
                "id": "azure_maps",
                "name": "Azure Maps",
                "requires_key": True,
                "free_tier": True
            },
            {
                "id": "bing_maps",
                "name": "Bing Maps (Deprecated)",
                "requires_key": True,
                "free_tier": False,
                "deprecated": True
            }
        ]
    }

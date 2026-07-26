"""API routes for user settings management."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from core.logging_config import get_logger
from models.user_settings import (
    CredentialValidationRequest,
    CredentialValidationResult,
    SettingsUpdate,
    UserSettings,
)
from services.settings_manager import get_settings_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

_VALIDATION_TIMEOUT = httpx.Timeout(15.0)


@router.get("", response_model=UserSettings)
@router.get("/", response_model=UserSettings, include_in_schema=False)
async def get_settings() -> UserSettings:
    """Get current user settings. API keys are masked."""
    try:
        return get_settings_manager().masked()
    except Exception as exc:
        logger.exception("Error getting settings")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings") from exc


@router.put("", response_model=UserSettings)
@router.put("/", response_model=UserSettings, include_in_schema=False)
async def update_settings(updates: SettingsUpdate) -> UserSettings:
    """
    Update user settings.

    Fields left out (or sent back as the masked placeholder the GET endpoint
    returns) are preserved rather than overwritten.
    """
    try:
        manager = get_settings_manager()
        updated = manager.update_settings(updates.model_dump(exclude_none=True))
        return manager.masked(updated)
    except Exception as exc:
        logger.exception("Error updating settings")
        raise HTTPException(status_code=500, detail="Failed to update settings") from exc


@router.post("/validate/{service}", response_model=CredentialValidationResult)
async def validate_api_key(
    service: str, payload: CredentialValidationRequest
) -> CredentialValidationResult:
    """
    Validate credentials by making a live test request to the provider.

    Supported services: ``sentinel_hub``, ``opentopography``, ``azure_maps``,
    ``bing_maps``.
    """
    validators = {
        "sentinel_hub": _validate_sentinel_hub,
        "opentopography": _validate_opentopography,
        "azure_maps": _validate_azure_maps,
        "bing_maps": _validate_bing_maps,
    }

    validator = validators.get(service)
    if validator is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service {service!r}. Supported: {', '.join(sorted(validators))}",
        )

    try:
        return await validator(payload)
    except httpx.HTTPError as exc:
        logger.warning("Network error validating %s credentials: %s", service, exc)
        return CredentialValidationResult(valid=False, error=f"Connection error: {exc}")
    except Exception:
        # Never surface the raw exception text: it can embed the submitted
        # credential (e.g. in a URL) and would then be rendered in the UI.
        logger.exception("Unexpected error validating %s credentials", service)
        return CredentialValidationResult(valid=False, error="Validation failed unexpectedly")


async def _validate_sentinel_hub(
    payload: CredentialValidationRequest,
) -> CredentialValidationResult:
    """
    Validate Sentinel Hub credentials via the OAuth2 client-credentials flow.

    The previous implementation sent the *client ID* as a bearer token, which
    the API always rejects - so valid credentials were reported as invalid
    100% of the time. Sentinel Hub issues a token from an ID/secret pair; that
    exchange is the only real check.
    """
    if not payload.api_secret:
        return CredentialValidationResult(
            valid=False,
            error="Sentinel Hub needs both a client ID and a client secret.",
        )

    async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT) as client:
        response = await client.post(
            "https://services.sentinel-hub.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": payload.api_key,
                "client_secret": payload.api_secret,
            },
        )

    if response.status_code == 200 and response.json().get("access_token"):
        return CredentialValidationResult(valid=True, message="Sentinel Hub credentials are valid")
    if response.status_code in (400, 401):
        return CredentialValidationResult(valid=False, error="Invalid client ID or secret")
    return CredentialValidationResult(
        valid=False, error=f"Unexpected response from Sentinel Hub: HTTP {response.status_code}"
    )


async def _validate_opentopography(
    payload: CredentialValidationRequest,
) -> CredentialValidationResult:
    """Validate an OpenTopography API key with a minimal DEM request."""
    async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT) as client:
        response = await client.get(
            "https://portal.opentopography.org/API/globaldem",
            params={
                "demtype": "SRTMGL3",
                "south": 37.00,
                "north": 37.01,
                "west": -119.60,
                "east": -119.59,
                "outputFormat": "GTiff",
                "API_Key": payload.api_key,
            },
        )

    if response.status_code == 200:
        return CredentialValidationResult(valid=True, message="OpenTopography API key is valid")
    if response.status_code in (401, 403):
        return CredentialValidationResult(valid=False, error="Invalid API key")
    if response.status_code == 429:
        return CredentialValidationResult(
            valid=False, error="Rate limited by OpenTopography - try again in a minute"
        )
    return CredentialValidationResult(
        valid=False, error=f"Unexpected response from OpenTopography: HTTP {response.status_code}"
    )


async def _validate_azure_maps(
    payload: CredentialValidationRequest,
) -> CredentialValidationResult:
    """Validate an Azure Maps subscription key with a single tile request."""
    async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT) as client:
        response = await client.get(
            "https://atlas.microsoft.com/map/tile",
            params={
                "api-version": "2.0",
                "tilesetId": "microsoft.imagery",
                "zoom": 1,
                "x": 0,
                "y": 0,
                "subscription-key": payload.api_key,
            },
        )

    if response.status_code == 200:
        return CredentialValidationResult(valid=True, message="Azure Maps subscription key is valid")
    if response.status_code in (401, 403):
        return CredentialValidationResult(valid=False, error="Invalid subscription key")
    return CredentialValidationResult(
        valid=False, error=f"Unexpected response from Azure Maps: HTTP {response.status_code}"
    )


async def _validate_bing_maps(payload: CredentialValidationRequest) -> CredentialValidationResult:
    """Validate a Bing Maps key. Bing Maps is retired; prefer Azure Maps."""
    async with httpx.AsyncClient(timeout=_VALIDATION_TIMEOUT) as client:
        response = await client.get(
            "https://dev.virtualearth.net/REST/v1/Imagery/Metadata/Aerial",
            params={"key": payload.api_key, "o": "json"},
        )

    if response.status_code == 200 and response.json().get("statusCode") == 200:
        return CredentialValidationResult(
            valid=True,
            message="Bing Maps API key is valid, but Bing Maps is deprecated - migrate to Azure Maps",
        )
    if response.status_code in (401, 403):
        return CredentialValidationResult(valid=False, error="Invalid API key")
    return CredentialValidationResult(
        valid=False, error=f"Unexpected response from Bing Maps: HTTP {response.status_code}"
    )


@router.get("/defaults")
async def get_defaults() -> dict:
    """Recommended defaults and the list of supported data sources."""
    return {
        "recommended_data_source": "opentopography",
        "recommended_image_source": "sentinel_hub",
        "supported_languages": ["en", "ru"],
        "data_sources": [
            {
                "id": "opentopography",
                "name": "OpenTopography",
                "requires_key": True,
                "free_tier": True,
                "provides": ["dem"],
            },
            {
                "id": "sentinel_hub",
                "name": "Sentinel Hub",
                "requires_key": True,
                "free_tier": True,
                "provides": ["dem", "imagery"],
            },
            {
                "id": "azure_maps",
                "name": "Azure Maps",
                "requires_key": True,
                "free_tier": True,
                "provides": ["imagery"],
            },
            {
                "id": "bing_maps",
                "name": "Bing Maps (retired by Microsoft)",
                "requires_key": True,
                "free_tier": False,
                "deprecated": True,
                "provides": ["imagery"],
            },
            {
                "id": "google_earth_engine",
                "name": "Google Earth Engine",
                "requires_key": True,
                "free_tier": True,
                "provides": ["dem", "imagery"],
            },
        ],
    }

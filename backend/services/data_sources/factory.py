"""
Factory for creating data source instances.

Two behaviours were fixed here:

* **Credentials from the UI are now used.** Clients previously read their keys
  only from ``os.environ``, so anything saved through the Settings page was
  silently ignored - the whole settings UI had no effect on generation. The
  factory now builds each client with credentials from the settings manager.
* **The cache is invalidated on change.** Instances are cached (they hold OAuth
  tokens worth reusing), but nothing cleared that cache, so even a restart-free
  key update could not take effect. A settings listener now clears it.
"""

from __future__ import annotations

import threading

from core.logging_config import get_logger

from .base import Capability, DataSourceInterface, DataSourceType

logger = get_logger(__name__)

#: Preference order when auto-selecting a source. Sentinel Hub first because it
#: is the only free source providing both DEM and imagery.
DEFAULT_DEM_PRIORITY = (
    DataSourceType.SENTINEL_HUB,
    DataSourceType.OPENTOPOGRAPHY,
    DataSourceType.GOOGLE_EARTH_ENGINE,
)

DEFAULT_IMAGERY_PRIORITY = (
    DataSourceType.SENTINEL_HUB,
    DataSourceType.AZURE_MAPS,
    DataSourceType.GOOGLE_EARTH_ENGINE,
)


class NoDataSourceAvailableError(RuntimeError):
    """Raised when no configured data source can serve a request."""


class DataSourceFactory:
    """Creates and caches data source instances."""

    _instances: dict[DataSourceType, DataSourceInterface] = {}
    _lock = threading.RLock()
    _listener_registered = False

    @classmethod
    def create(
        cls,
        source_type: DataSourceType,
        config: dict | None = None,
        force_recreate: bool = False,
    ) -> DataSourceInterface:
        """
        Create or return a cached data source instance.

        Args:
            source_type: Which source to build.
            config: Explicit credentials. When omitted, the user's saved
                settings are used.
            force_recreate: Rebuild even if a cached instance exists.

        Returns:
            A ready-to-use :class:`DataSourceInterface`.
        """
        cls._ensure_listener()

        # An explicit config is a one-off (validation, tests) and must not be
        # cached, or it would poison later calls that expect saved credentials.
        if config is not None:
            return cls._instantiate(source_type, config)

        with cls._lock:
            if not force_recreate and source_type in cls._instances:
                return cls._instances[source_type]

            instance = cls._instantiate(source_type, cls._credentials_for(source_type))
            cls._instances[source_type] = instance
            return instance

    @classmethod
    def get_default_source(cls) -> DataSourceInterface:
        """Return the best available source for elevation data."""
        source = cls.first_available(DEFAULT_DEM_PRIORITY, Capability.DEM)
        if source is None:
            raise NoDataSourceAvailableError(
                "No elevation data source is available. Configure at least one in Settings:\n"
                "  - OpenTopography (free API key, DEM only)\n"
                "  - Sentinel Hub (free tier, DEM + satellite imagery)\n"
                "  - Google Earth Engine (requires a Google Cloud service account)"
            )
        return source

    @classmethod
    def get_imagery_source(cls) -> DataSourceInterface:
        """Return the best available source for satellite imagery."""
        source = cls.first_available(DEFAULT_IMAGERY_PRIORITY, Capability.IMAGERY)
        if source is None:
            raise NoDataSourceAvailableError(
                "No satellite imagery source is available. Configure Sentinel Hub or "
                "Azure Maps in Settings to enable imagery-based features."
            )
        return source

    @classmethod
    def first_available(
        cls,
        priority: tuple[DataSourceType, ...],
        capability: Capability,
    ) -> DataSourceInterface | None:
        """Return the first source in ``priority`` that is available and capable."""
        for source_type in priority:
            try:
                source = cls.create(source_type)
            except Exception as exc:  # noqa: BLE001 - a broken client must not stop the search
                logger.debug("Could not construct %s: %s", source_type.value, exc)
                continue

            if not source.provides(capability):
                continue
            if source.is_available():
                logger.info("Selected %s for %s", source.get_source_name(), capability.value)
                return source

        return None

    @classmethod
    def get_available_sources(cls) -> list[DataSourceType]:
        """Return the source types that are currently usable."""
        available = []
        for source_type in DataSourceType:
            try:
                if cls.create(source_type).is_available():
                    available.append(source_type)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping %s: %s", source_type.value, exc)
        return available

    @classmethod
    def clear_cache(cls) -> None:
        """Drop all cached instances so the next call picks up new credentials."""
        with cls._lock:
            cls._instances.clear()
        logger.debug("Data source cache cleared")

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _instantiate(source_type: DataSourceType, config: dict) -> DataSourceInterface:
        """Import and construct the client for ``source_type``."""
        # Imports are local so that a missing optional dependency (notably the
        # Earth Engine SDK) only breaks the source that needs it.
        if source_type is DataSourceType.SENTINEL_HUB:
            from .sentinel_hub_client import SentinelHubDataSource

            return SentinelHubDataSource(config)

        if source_type is DataSourceType.OPENTOPOGRAPHY:
            from .opentopography_client import OpenTopographyDataSource

            return OpenTopographyDataSource(config)

        if source_type is DataSourceType.BING_MAPS:
            from .bing_maps_client import BingMapsDataSource

            return BingMapsDataSource(config)

        if source_type is DataSourceType.AZURE_MAPS:
            from .azure_maps_client import AzureMapsDataSource

            return AzureMapsDataSource(config)

        if source_type is DataSourceType.GOOGLE_EARTH_ENGINE:
            from .gee_adapter import GEEDataSource

            return GEEDataSource(config)

        raise ValueError(f"Unknown data source type: {source_type}")

    @staticmethod
    def _credentials_for(source_type: DataSourceType) -> dict:
        """Load saved credentials for a source, tolerating an unreadable store."""
        try:
            from services.settings_manager import get_settings_manager

            return get_settings_manager().credentials_for(source_type.value)
        except Exception as exc:  # noqa: BLE001 - fall back to env vars
            logger.warning("Could not load saved credentials for %s: %s", source_type.value, exc)
            return {}

    @classmethod
    def _ensure_listener(cls) -> None:
        """Subscribe to settings changes so the cache is invalidated on save."""
        if cls._listener_registered:
            return
        try:
            from services.settings_manager import get_settings_manager

            get_settings_manager().on_change(lambda _settings: cls.clear_cache())
            cls._listener_registered = True
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not subscribe to settings changes: %s", exc)

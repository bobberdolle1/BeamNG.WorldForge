"""Base interface for geodata sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

import numpy as np

from core.logging_config import get_logger

logger = get_logger(__name__)


class DataSourceType(StrEnum):
    """Available data source types."""

    SENTINEL_HUB = "sentinel_hub"
    OPENTOPOGRAPHY = "opentopography"
    BING_MAPS = "bing_maps"  # Retired by Microsoft - use AZURE_MAPS instead.
    AZURE_MAPS = "azure_maps"
    GOOGLE_EARTH_ENGINE = "google_earth_engine"


class Capability(StrEnum):
    """What a data source can supply."""

    DEM = "dem"
    IMAGERY = "imagery"


class DataSourceError(RuntimeError):
    """Raised when a data source cannot fulfil a request."""


class DataSourceUnavailableError(DataSourceError):
    """Raised when a data source is not configured or not reachable."""


class DataSourceInterface(ABC):
    """
    Abstract interface for geodata sources.

    All data sources implement these methods to provide DEM and satellite
    imagery in a unified format.
    """

    #: What this source can provide. Declared per subclass so callers can pick
    #: an imagery-capable source without calling a method and catching
    #: NotImplementedError, which is how the pipeline used to discover it.
    capabilities: frozenset[Capability] = frozenset()

    def __init__(self, config: dict | None = None) -> None:
        """
        Args:
            config: Credentials and options. Supplied by the factory from the
                user's saved settings; falls back to environment variables.
        """
        self.config = config or {}

    # -- data retrieval -------------------------------------------------------

    @abstractmethod
    def get_dem_data(self, bbox: list, resolution: int = 30) -> tuple[np.ndarray, dict]:
        """
        Fetch Digital Elevation Model data.

        Args:
            bbox: ``[min_lon, min_lat, max_lon, max_lat]``.
            resolution: Ground resolution in metres.

        Returns:
            ``(elevation array [H, W] in metres, metadata dict)``.
        """

    @abstractmethod
    def get_satellite_image(self, bbox: list, resolution: int = 10) -> tuple[np.ndarray, dict]:
        """
        Fetch an RGB satellite image.

        Args:
            bbox: ``[min_lon, min_lat, max_lon, max_lat]``.
            resolution: Ground resolution in metres.

        Returns:
            ``(uint8 RGB array [H, W, 3], metadata dict)``.
        """

    # -- capability / availability -------------------------------------------

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the source is configured and reachable."""

    @abstractmethod
    def requires_setup(self) -> bool:
        """Return True if the user must supply credentials before use."""

    def provides(self, capability: Capability) -> bool:
        """Return True if this source can supply ``capability``."""
        return capability in self.capabilities

    def get_source_name(self) -> str:
        """Human-readable name."""
        return self.__class__.__name__

    def get_source_description(self) -> str:
        """Human-readable description shown in the data source picker."""
        return "Data source for elevation and satellite imagery"

    def is_available(self) -> bool:
        """
        Return True if the source is ready to use.

        Never raises: callers use this to build the "available sources" list,
        and one misconfigured provider must not break the whole listing.
        """
        try:
            return self.test_connection()
        except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
            logger.info("%s is not available: %s", self.get_source_name(), exc)
            return False


class DataSourceMetadata:
    """Metadata describing a data source response."""

    def __init__(
        self,
        bounds: tuple[float, float, float, float],
        crs: str,
        width: int,
        height: int,
        resolution: float,
        source_type: DataSourceType,
        additional: dict | None = None,
    ) -> None:
        self.bounds = bounds  # (min_lon, min_lat, max_lon, max_lat)
        self.crs = crs
        self.width = width
        self.height = height
        self.resolution = resolution
        self.source_type = source_type
        self.additional = additional or {}

    def to_dict(self) -> dict:
        """Convert to a plain dictionary."""
        return {
            "bounds": self.bounds,
            "crs": self.crs,
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "source_type": self.source_type.value,
            **self.additional,
        }

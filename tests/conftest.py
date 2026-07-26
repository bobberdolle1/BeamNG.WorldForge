"""Shared pytest fixtures.

Every test runs against an isolated temporary data root so nothing touches the
developer's real ``backend/output``, ``backend/temp`` or - importantly - their
``backend/config/settings.key``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Point every configurable directory at a per-test temp dir."""
    from core import config as config_module

    for name in ("OUTPUT_DIR", "TEMP_DIR", "CONFIG_DIR"):
        monkeypatch.setenv(name, str(tmp_path / name.lower().replace("_dir", "")))

    # Credentials must never leak in from the developer's shell: a test that
    # asserts "source unavailable" would pass or fail depending on whose
    # machine it runs on.
    for name in (
        "SENTINEL_HUB_CLIENT_ID",
        "SENTINEL_HUB_CLIENT_SECRET",
        "OPENTOPOGRAPHY_API_KEY",
        "AZURE_MAPS_SUBSCRIPTION_KEY",
        "BING_MAPS_API_KEY",
        "GEE_PROJECT_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    settings.ensure_directories()

    from services.settings_manager import reset_settings_manager

    reset_settings_manager()

    yield settings

    config_module.get_settings.cache_clear()
    reset_settings_manager()


@pytest.fixture
def settings(isolated_environment):
    """The isolated Settings instance for this test."""
    return isolated_environment


@pytest.fixture
def job_store():
    """A fresh job store."""
    from services.jobs import JobStore

    return JobStore(retention_seconds=3600)


@pytest.fixture
def sample_dem() -> np.ndarray:
    """A small synthetic DEM: a smooth hill from 100 m to ~340 m."""
    rows, cols = 64, 96
    y, x = np.mgrid[0:rows, 0:cols]
    hill = 240.0 * np.exp(-(((x - cols / 2) / 20.0) ** 2 + ((y - rows / 2) / 14.0) ** 2))
    return (100.0 + hill).astype(np.float32)


@pytest.fixture
def bbox() -> list[float]:
    """A ~2.6 x 3.3 km box over San Francisco: [min_lon, min_lat, max_lon, max_lat]."""
    return [-122.4294, 37.7749, -122.3994, 37.8049]

"""
Application configuration.

Single source of truth for every tunable in the backend. Values are read from
environment variables (optionally via a ``.env`` file) and validated by
pydantic-settings, so a typo in a variable name fails loudly at startup instead
of silently falling back to a default deep inside a service.

All directory settings are resolved to *absolute* paths against
:data:`APP_ROOT`. This matters because the app can run in three different
working directories:

* ``backend/`` during development (``uvicorn main:app``)
* the repository root (``python build.py`` output, Docker)
* a PyInstaller temp dir (``sys._MEIPASS``) for the standalone executable

Before this module, ``Path("output")`` and ``Path("temp")`` were resolved
against whatever ``cwd`` happened to be, so a generated map could land in an
unpredictable place - or be written next to the user's shell.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _bundle_dir() -> Path:
    """Directory holding bundled read-only resources (static assets)."""
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _writable_root() -> Path:
    """
    Directory for data the app *writes* (config, output, temp).

    A PyInstaller bundle unpacks into a temp directory that is deleted on exit,
    so writing user data there would silently lose it between runs. In frozen
    mode we therefore anchor writable state next to the executable.
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


#: Directory containing bundled resources (``backend/`` or the PyInstaller temp dir).
APP_ROOT = _bundle_dir()

#: Directory under which all writable state lives.
DATA_ROOT = _writable_root()


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=(DATA_ROOT / ".env", Path.cwd() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- Server ---------------------------------------------------------------
    api_host: str = Field("127.0.0.1", description="Interface the API binds to")
    api_port: int = Field(8000, ge=1, le=65535, description="Port the API listens on")
    api_reload: bool = Field(False, description="Enable uvicorn auto-reload (development only)")
    log_level: str = Field("INFO", description="Root log level")

    cors_origins: str = Field(
        "http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed browser origins",
    )

    # -- Storage --------------------------------------------------------------
    output_dir: Path = Field(Path("output"), description="Where finished map archives are written")
    temp_dir: Path = Field(Path("temp"), description="Scratch space for intermediate artefacts")
    config_dir: Path = Field(Path("config"), description="Where encrypted settings live")
    static_dir: Path = Field(Path("static"), description="Bundled frontend build")

    # -- Job lifecycle --------------------------------------------------------
    job_retention_seconds: int = Field(
        24 * 60 * 60,
        ge=60,
        description="How long a finished job (and its artefacts) is kept before cleanup",
    )
    max_concurrent_jobs: int = Field(
        2, ge=1, le=16, description="Maximum map generations running at the same time"
    )

    # -- Data sources ---------------------------------------------------------
    default_data_source: str = Field("auto", description="Data source used when the request says 'auto'")
    http_timeout_seconds: float = Field(120.0, gt=0, description="Timeout for outbound geodata requests")

    # -- AI (optional) --------------------------------------------------------
    ollama_base_url: str = Field(
        "http://localhost:11434",
        validation_alias="OLLAMA_HOST",
        description="Ollama endpoint (env var: OLLAMA_HOST)",
    )
    ollama_vl_model: str = Field("qwen3-vl:235b-cloud", description="Vision model for segmentation")
    ollama_coder_model: str = Field("qwen3-coder:480b-cloud", description="Code model for JBeam generation")
    ollama_timeout_seconds: float = Field(300.0, gt=0, description="Timeout for Ollama requests")

    @field_validator("output_dir", "temp_dir", "config_dir", "static_dir", mode="after")
    @classmethod
    def _absolutise(cls, value: Path) -> Path:
        """Resolve relative directories against the writable root, not ``cwd``."""
        if value.is_absolute():
            return value
        return (DATA_ROOT / value).resolve()

    @field_validator("log_level", mode="after")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        level = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if level not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got {value!r}")
        return level

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list, with blanks stripped."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def bundled_static_dir(self) -> Path:
        """
        Frontend build directory.

        Static assets are read-only and ship *inside* the bundle, so they are
        resolved against :data:`APP_ROOT` rather than the writable root.
        """
        if self.static_dir.is_absolute() and self.static_dir.exists():
            return self.static_dir
        return APP_ROOT / "static"

    def ensure_directories(self) -> None:
        """Create the writable directories the app depends on."""
        for directory in (self.output_dir, self.temp_dir, self.config_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


def reload_settings() -> Settings:
    """Drop the cached settings and re-read the environment (used by tests)."""
    get_settings.cache_clear()
    return get_settings()

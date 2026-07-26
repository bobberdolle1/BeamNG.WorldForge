"""
Secure settings storage.

User-supplied API keys are encrypted at rest with Fernet. Two important
properties this module now guarantees that the previous version did not:

* **Masked values never overwrite real secrets.** The API returns keys masked
  (``***abcd``). If the UI submitted the form back unchanged, that mask used to
  be written to disk as the new secret, silently destroying the real key.
  :func:`is_masked_value` detects and discards those.
* **Change notification.** Data source clients cache their credentials, so a
  key saved through the UI had no effect until the process restarted.
  Listeners registered via :meth:`SettingsManager.on_change` are invoked after
  every successful save.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings
from core.logging_config import get_logger
from models.user_settings import APIKeys, UserPreferences, UserSettings

logger = get_logger(__name__)

#: Prefix used when masking a secret for display.
MASK_PREFIX = "***"

#: Number of trailing characters left visible in a masked secret.
MASK_VISIBLE_SUFFIX = 4

#: Environment variable backing each API key field.
ENV_VAR_BY_FIELD = {
    "sentinel_hub_client_id": "SENTINEL_HUB_CLIENT_ID",
    "sentinel_hub_client_secret": "SENTINEL_HUB_CLIENT_SECRET",
    "opentopography_api_key": "OPENTOPOGRAPHY_API_KEY",
    "azure_maps_subscription_key": "AZURE_MAPS_SUBSCRIPTION_KEY",
    "bing_maps_api_key": "BING_MAPS_API_KEY",
    "gee_project_id": "GEE_PROJECT_ID",
}

#: Fields that must never be returned to the client in the clear.
SECRET_FIELDS = frozenset(
    {
        "sentinel_hub_client_id",
        "sentinel_hub_client_secret",
        "opentopography_api_key",
        "azure_maps_subscription_key",
        "bing_maps_api_key",
    }
)


def mask_secret(value: str | None) -> str | None:
    """Mask a secret for display, keeping only the last few characters."""
    if not value:
        return value
    if len(value) <= MASK_VISIBLE_SUFFIX:
        return MASK_PREFIX
    return f"{MASK_PREFIX}{value[-MASK_VISIBLE_SUFFIX:]}"


def is_masked_value(value: str | None) -> bool:
    """
    True if ``value`` looks like a mask this server produced.

    Used to drop round-tripped masks on update so a user who edits only their
    preferences does not wipe out their stored API keys.
    """
    return bool(value) and value.startswith(MASK_PREFIX)


class SettingsManager:
    """Manages encrypted storage and retrieval of user settings."""

    def __init__(self, config_dir: Path | str | None = None) -> None:
        self.config_dir = Path(config_dir) if config_dir else get_settings().config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.config_dir / "user_settings.enc"
        self.key_file = self.config_dir / "settings.key"

        self._listeners: list[Callable[[UserSettings], None]] = []
        self._cipher = self._init_cipher()

    # -- encryption key -------------------------------------------------------

    def _init_cipher(self) -> Fernet:
        """Load the Fernet key, generating one on first run."""
        if self.key_file.exists():
            key = self.key_file.read_bytes().strip()
            self._warn_if_world_readable()
        else:
            key = Fernet.generate_key()
            # Create with restrictive permissions from the start rather than
            # writing first and chmod-ing after, which leaves a window where
            # the key is world-readable.
            descriptor = os.open(self.key_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(key)
            logger.info("Generated new settings encryption key at %s", self.key_file)

        return Fernet(key)

    def _warn_if_world_readable(self) -> None:
        """Warn when the key file is readable by other users on the system."""
        try:
            mode = self.key_file.stat().st_mode
        except OSError:  # pragma: no cover - unreadable stat is already fatal elsewhere
            return
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            logger.warning(
                "%s is readable by other users. Restrict it with: chmod 600 %s",
                self.key_file,
                self.key_file,
            )

    # -- change notification --------------------------------------------------

    def on_change(self, listener: Callable[[UserSettings], None]) -> None:
        """Register a callback invoked after settings are saved."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _notify(self, settings: UserSettings) -> None:
        for listener in self._listeners:
            try:
                listener(settings)
            except Exception:  # noqa: BLE001 - a bad listener must not break saving
                logger.exception("Settings change listener failed")

    # -- load / save ----------------------------------------------------------

    def load_settings(self) -> UserSettings:
        """
        Load settings, merging the encrypted file with environment variables.

        Environment variables win for API keys (so a deployment can inject
        credentials without a writable config dir); the file wins for
        preferences (so UI changes stick).
        """
        env_settings = self._load_from_env()

        if not self.settings_file.exists():
            return env_settings

        try:
            decrypted = self._cipher.decrypt(self.settings_file.read_bytes())
            file_settings = UserSettings(**json.loads(decrypted.decode("utf-8")))
        except InvalidToken:
            logger.error(
                "Could not decrypt %s - the encryption key does not match. "
                "Delete the file to start fresh; stored API keys will be lost.",
                self.settings_file,
            )
            return env_settings
        except (OSError, ValueError) as exc:
            logger.error("Could not read settings from %s: %s", self.settings_file, exc)
            return env_settings

        return self._merge_settings(file_settings, env_settings)

    def save_settings(self, settings: UserSettings) -> bool:
        """Encrypt and persist settings. Returns True on success."""
        try:
            payload = self._cipher.encrypt(settings.model_dump_json().encode("utf-8"))

            # Write to a temp file then rename, so an interrupted write cannot
            # leave a truncated (undecryptable) settings file behind.
            temp_file = self.settings_file.with_suffix(".enc.tmp")
            descriptor = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
            temp_file.replace(self.settings_file)
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)
            return False

        logger.info("Settings saved to %s", self.settings_file)
        self._notify(settings)
        return True

    def update_settings(self, updates: dict) -> UserSettings:
        """
        Apply a partial update and persist the result.

        ``None`` values and masked placeholders are ignored so a partial form
        submission cannot erase stored credentials.
        """
        current = self.load_settings()

        if updates.get("api_keys"):
            api_keys = current.api_keys.model_dump()
            for field, value in updates["api_keys"].items():
                if value is None:
                    continue
                if is_masked_value(value):
                    logger.debug("Ignoring masked placeholder for %s", field)
                    continue
                # An explicit empty string is a deliberate "clear this key".
                api_keys[field] = value.strip() or None
            current.api_keys = APIKeys(**api_keys)

        if updates.get("preferences"):
            preferences = current.preferences.model_dump()
            preferences.update(
                {key: value for key, value in updates["preferences"].items() if value is not None}
            )
            current.preferences = UserPreferences(**preferences)

        self.save_settings(current)
        return current

    def masked(self, settings: UserSettings | None = None) -> UserSettings:
        """Return a copy of the settings with every secret masked."""
        source = settings or self.load_settings()
        copy = source.model_copy(deep=True)
        for field in SECRET_FIELDS:
            setattr(copy.api_keys, field, mask_secret(getattr(copy.api_keys, field)))
        return copy

    # -- accessors ------------------------------------------------------------

    def get_api_key(self, field: str) -> str | None:
        """Return a single API key by its field name."""
        return getattr(self.load_settings().api_keys, field, None)

    def credentials_for(self, source_id: str) -> dict[str, str]:
        """
        Build the config dict a data source client expects.

        Keeps the mapping between stored fields and client kwargs in one place
        instead of scattering ``os.getenv`` calls across every client.
        """
        keys = self.load_settings().api_keys
        mapping: dict[str, dict[str, str | None]] = {
            "sentinel_hub": {
                "client_id": keys.sentinel_hub_client_id,
                "client_secret": keys.sentinel_hub_client_secret,
            },
            "opentopography": {"api_key": keys.opentopography_api_key},
            "azure_maps": {"subscription_key": keys.azure_maps_subscription_key},
            "bing_maps": {"api_key": keys.bing_maps_api_key},
            "google_earth_engine": {"project_id": keys.gee_project_id},
        }
        return {key: value for key, value in mapping.get(source_id, {}).items() if value}

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _load_from_env() -> UserSettings:
        """Read settings from environment variables."""
        return UserSettings(
            api_keys=APIKeys(
                **{field: os.getenv(env) for field, env in ENV_VAR_BY_FIELD.items()}
            ),
            preferences=UserPreferences(
                default_data_source=os.getenv("DEFAULT_DATA_SOURCE", "auto"),
                default_image_source=os.getenv("DEFAULT_IMAGE_SOURCE", "sentinel_hub"),
                language=os.getenv("UI_LANGUAGE", "en"),
            ),
        )

    @staticmethod
    def _merge_settings(file_settings: UserSettings, env_settings: UserSettings) -> UserSettings:
        """Merge file and env settings: env wins for keys, file wins for preferences."""
        merged = {
            field: getattr(env_settings.api_keys, field) or getattr(file_settings.api_keys, field)
            for field in file_settings.api_keys.model_dump()
        }
        return UserSettings(
            api_keys=APIKeys(**merged),
            preferences=file_settings.preferences,
        )


_manager: SettingsManager | None = None


def get_settings_manager() -> SettingsManager:
    """
    Return the process-wide settings manager, creating it on first use.

    Lazy rather than module-level so importing this module does not create a
    ``config/`` directory as a side effect - which used to happen in whatever
    directory the process was started from, and broke test collection.
    """
    global _manager
    if _manager is None:
        _manager = SettingsManager()
    return _manager


def reset_settings_manager() -> None:
    """Drop the cached manager (tests only)."""
    global _manager
    _manager = None

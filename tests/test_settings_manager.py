"""Encrypted settings storage: masking, merge rules, key file permissions."""

from __future__ import annotations

import json
import os
import stat

import pytest
from cryptography.fernet import Fernet

from models.user_settings import APIKeys, UserPreferences, UserSettings
from services.settings_manager import (
    SettingsManager,
    is_masked_value,
    mask_secret,
)


@pytest.fixture
def manager(tmp_path):
    return SettingsManager(config_dir=tmp_path / "config")


def test_generates_key_with_owner_only_permissions(manager):
    assert manager.key_file.exists()

    mode = manager.key_file.stat().st_mode
    assert not mode & stat.S_IRGRP, "key must not be group readable"
    assert not mode & stat.S_IROTH, "key must not be world readable"


def test_settings_file_is_encrypted_on_disk(manager):
    manager.save_settings(
        UserSettings(api_keys=APIKeys(opentopography_api_key="super-secret-value"))
    )

    raw = manager.settings_file.read_bytes()
    assert b"super-secret-value" not in raw
    with pytest.raises(Exception):
        json.loads(raw)


def test_round_trip_preserves_values(manager):
    manager.save_settings(
        UserSettings(
            api_keys=APIKeys(sentinel_hub_client_id="id-1", sentinel_hub_client_secret="secret-1"),
            preferences=UserPreferences(language="ru"),
        )
    )

    loaded = manager.load_settings()
    assert loaded.api_keys.sentinel_hub_client_id == "id-1"
    assert loaded.api_keys.sentinel_hub_client_secret == "secret-1"
    assert loaded.preferences.language == "ru"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", ""),
        ("abcd", "***"),
        ("abc", "***"),
        ("0123456789abcdef", "***cdef"),
    ],
)
def test_mask_secret(value, expected):
    assert mask_secret(value) == expected


def test_masked_view_hides_every_secret(manager):
    manager.save_settings(
        UserSettings(
            api_keys=APIKeys(
                sentinel_hub_client_id="client-id-value",
                sentinel_hub_client_secret="client-secret-value",
                opentopography_api_key="opentopo-key-value",
                azure_maps_subscription_key="azure-key-value",
                bing_maps_api_key="bing-key-value",
                gee_project_id="my-gcp-project",
            )
        )
    )

    masked = manager.masked()
    for field in (
        "sentinel_hub_client_id",
        "sentinel_hub_client_secret",
        "opentopography_api_key",
        "azure_maps_subscription_key",
        "bing_maps_api_key",
    ):
        assert is_masked_value(getattr(masked.api_keys, field)), field

    # A GCP project id is not a secret and stays readable so the UI can show it.
    assert masked.api_keys.gee_project_id == "my-gcp-project"


def test_masked_placeholder_does_not_overwrite_stored_secret(manager):
    """
    Regression: the UI reads settings (masked), the user edits an unrelated
    field, and the form posts every value back. The mask used to be saved as
    the new secret, destroying the real key.
    """
    manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="real-key-12345")))

    masked = manager.masked()
    manager.update_settings(
        {
            "api_keys": masked.api_keys.model_dump(),
            "preferences": {"language": "ru"},
        }
    )

    assert manager.load_settings().api_keys.opentopography_api_key == "real-key-12345"
    assert manager.load_settings().preferences.language == "ru"


def test_empty_string_clears_a_key(manager):
    manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="to-be-removed")))
    manager.update_settings({"api_keys": {"opentopography_api_key": ""}})

    assert manager.load_settings().api_keys.opentopography_api_key is None


def test_environment_variables_take_precedence_over_file(manager, monkeypatch):
    manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="from-file")))
    monkeypatch.setenv("OPENTOPOGRAPHY_API_KEY", "from-env")

    assert manager.load_settings().api_keys.opentopography_api_key == "from-env"


def test_file_preferences_win_over_environment(manager, monkeypatch):
    manager.save_settings(UserSettings(preferences=UserPreferences(language="ru")))
    monkeypatch.setenv("UI_LANGUAGE", "en")

    assert manager.load_settings().preferences.language == "ru"


def test_undecryptable_file_falls_back_to_env_instead_of_crashing(manager, monkeypatch):
    manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="lost")))

    # Simulate a key rotation / restored-from-backup mismatch.
    manager.settings_file.write_bytes(Fernet(Fernet.generate_key()).encrypt(b"{}"))
    monkeypatch.setenv("OPENTOPOGRAPHY_API_KEY", "env-fallback")

    assert manager.load_settings().api_keys.opentopography_api_key == "env-fallback"


def test_change_listeners_fire_on_save(manager):
    seen = []
    manager.on_change(seen.append)

    manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="x")))

    assert len(seen) == 1


def test_broken_listener_does_not_break_saving(manager):
    def explode(_settings):
        raise RuntimeError("listener is broken")

    manager.on_change(explode)
    assert manager.save_settings(UserSettings()) is True


def test_credentials_for_builds_client_config(manager):
    manager.save_settings(
        UserSettings(
            api_keys=APIKeys(
                sentinel_hub_client_id="cid",
                sentinel_hub_client_secret="csec",
                opentopography_api_key="otk",
            )
        )
    )

    assert manager.credentials_for("sentinel_hub") == {"client_id": "cid", "client_secret": "csec"}
    assert manager.credentials_for("opentopography") == {"api_key": "otk"}
    # Unset credentials are omitted entirely rather than passed as None.
    assert manager.credentials_for("azure_maps") == {}
    assert manager.credentials_for("unknown_source") == {}


def test_interrupted_write_leaves_previous_settings_intact(manager, monkeypatch):
    manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="original")))

    real_replace = os.replace

    def fail_replace(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.replace", lambda *a, **k: fail_replace())
    assert manager.save_settings(UserSettings(api_keys=APIKeys(opentopography_api_key="new"))) is False

    monkeypatch.setattr(os, "replace", real_replace)
    assert manager.load_settings().api_keys.opentopography_api_key == "original"

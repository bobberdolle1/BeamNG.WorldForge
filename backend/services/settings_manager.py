"""Secure settings storage manager with encryption"""

import json
import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from models.user_settings import UserSettings, APIKeys, UserPreferences
import logging

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages secure storage and retrieval of user settings"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.config_dir / "user_settings.enc"
        self.key_file = self.config_dir / "settings.key"
        
        # Initialize encryption key
        self._init_encryption_key()
        
    def _init_encryption_key(self):
        """Initialize or load encryption key"""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            # Generate new key
            self.key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self.key)
            # Secure the key file (Unix-like systems)
            try:
                os.chmod(self.key_file, 0o600)
            except Exception as e:
                logger.warning(f"Could not set key file permissions: {e}")
        
        self.cipher = Fernet(self.key)
    
    def load_settings(self) -> UserSettings:
        """Load user settings from encrypted storage"""
        # First, try to load from environment variables (backward compatibility)
        env_settings = self._load_from_env()
        
        # Then try to load from encrypted file
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = self.cipher.decrypt(encrypted_data)
                settings_dict = json.loads(decrypted_data.decode())
                file_settings = UserSettings(**settings_dict)
                
                # Merge with env settings (env takes precedence for non-empty values)
                return self._merge_settings(file_settings, env_settings)
            except Exception as e:
                logger.error(f"Error loading settings from file: {e}")
                return env_settings
        
        return env_settings
    
    def save_settings(self, settings: UserSettings) -> bool:
        """Save user settings to encrypted storage"""
        try:
            settings_json = settings.model_dump_json()
            encrypted_data = self.cipher.encrypt(settings_json.encode())
            
            with open(self.settings_file, "wb") as f:
                f.write(encrypted_data)
            
            # Secure the settings file
            try:
                os.chmod(self.settings_file, 0o600)
            except Exception as e:
                logger.warning(f"Could not set settings file permissions: {e}")
            
            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def update_settings(self, updates: dict) -> UserSettings:
        """Update specific settings while preserving others"""
        current_settings = self.load_settings()
        
        # Update API keys if provided
        if "api_keys" in updates:
            api_keys_dict = current_settings.api_keys.model_dump()
            api_keys_dict.update({k: v for k, v in updates["api_keys"].items() if v is not None})
            current_settings.api_keys = APIKeys(**api_keys_dict)
        
        # Update preferences if provided
        if "preferences" in updates:
            prefs_dict = current_settings.preferences.model_dump()
            prefs_dict.update({k: v for k, v in updates["preferences"].items() if v is not None})
            current_settings.preferences = UserPreferences(**prefs_dict)
        
        self.save_settings(current_settings)
        return current_settings
    
    def _load_from_env(self) -> UserSettings:
        """Load settings from environment variables (backward compatibility)"""
        return UserSettings(
            api_keys=APIKeys(
                sentinel_hub_client_id=os.getenv("SENTINEL_HUB_CLIENT_ID"),
                sentinel_hub_client_secret=os.getenv("SENTINEL_HUB_CLIENT_SECRET"),
                opentopography_api_key=os.getenv("OPENTOPOGRAPHY_API_KEY"),
                azure_maps_subscription_key=os.getenv("AZURE_MAPS_SUBSCRIPTION_KEY"),
                bing_maps_api_key=os.getenv("BING_MAPS_API_KEY"),
                gee_project_id=os.getenv("GEE_PROJECT_ID")
            ),
            preferences=UserPreferences(
                default_data_source=os.getenv("DEFAULT_DATA_SOURCE", "opentopography"),
                default_image_source=os.getenv("DEFAULT_IMAGE_SOURCE", "sentinel_hub"),
                language=os.getenv("UI_LANGUAGE", "en")
            )
        )
    
    def _merge_settings(self, file_settings: UserSettings, env_settings: UserSettings) -> UserSettings:
        """Merge file and environment settings, with env taking precedence for non-empty values"""
        merged_api_keys = {}
        
        # Merge API keys
        for key in file_settings.api_keys.model_dump().keys():
            file_val = getattr(file_settings.api_keys, key)
            env_val = getattr(env_settings.api_keys, key)
            # Environment variable takes precedence if set
            merged_api_keys[key] = env_val if env_val else file_val
        
        return UserSettings(
            api_keys=APIKeys(**merged_api_keys),
            preferences=file_settings.preferences  # File preferences take precedence
        )
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a specific service"""
        settings = self.load_settings()
        key_mapping = {
            "sentinel_hub_id": settings.api_keys.sentinel_hub_client_id,
            "sentinel_hub_secret": settings.api_keys.sentinel_hub_client_secret,
            "opentopography": settings.api_keys.opentopography_api_key,
            "azure_maps": settings.api_keys.azure_maps_subscription_key,
            "bing_maps": settings.api_keys.bing_maps_api_key,
            "gee": settings.api_keys.gee_project_id
        }
        return key_mapping.get(service)


# Global settings manager instance
settings_manager = SettingsManager()

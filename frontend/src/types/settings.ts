/**
 * Types for user settings and API keys
 */

export interface APIKeys {
  sentinel_hub_client_id?: string;
  sentinel_hub_client_secret?: string;
  opentopography_api_key?: string;
  azure_maps_subscription_key?: string;
  bing_maps_api_key?: string;
  gee_project_id?: string;
}

export interface UserPreferences {
  default_data_source: string;
  default_image_source: string;
  language: string;
}

export interface UserSettings {
  api_keys: APIKeys;
  preferences: UserPreferences;
}

export interface ValidationResult {
  valid: boolean;
  message?: string;
  error?: string;
}

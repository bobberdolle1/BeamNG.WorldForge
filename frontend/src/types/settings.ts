/**
 * Types for user settings and API keys.
 *
 * Mirrors `backend/models/user_settings.py`.
 */

export interface APIKeys {
  sentinel_hub_client_id?: string | null
  sentinel_hub_client_secret?: string | null
  opentopography_api_key?: string | null
  azure_maps_subscription_key?: string | null
  bing_maps_api_key?: string | null
  gee_project_id?: string | null
}

export type APIKeyField = keyof APIKeys

export interface UserPreferences {
  default_data_source: string
  default_image_source: string
  language: string
}

export interface UserSettings {
  api_keys: APIKeys
  preferences: UserPreferences
}

export interface ValidationResult {
  valid: boolean
  message?: string | null
  error?: string | null
}

/**
 * Services the backend can validate credentials against.
 *
 * Deliberately narrow. The settings page used to offer a Verify button for
 * `gee`, which the backend has never supported - every click returned 400.
 */
export const VALIDATABLE_SERVICES = [
  'sentinel_hub',
  'opentopography',
  'azure_maps',
  'bing_maps',
] as const

export type ValidatableService = (typeof VALIDATABLE_SERVICES)[number]

/** Prefix the backend uses when masking a stored secret for display. */
export const MASK_PREFIX = '***'

/**
 * True if a value is a mask the server produced rather than a real secret.
 *
 * The GET endpoint returns secrets as `***abcd`. Treating that as an editable
 * value means the user cannot tell "configured" from "literally ***abcd", and
 * sending it back as a credential to validate is guaranteed to fail.
 */
export function isMasked(value: string | null | undefined): boolean {
  return typeof value === 'string' && value.startsWith(MASK_PREFIX)
}

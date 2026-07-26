import { Check, Eye, EyeOff, Info, Loader2, Save, Settings, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { getSettings, saveSettings, validateCredential } from '../services/api'
import type {
  APIKeyField,
  APIKeys,
  UserSettings,
  ValidatableService,
  ValidationResult,
} from '../types/settings'
import { isMasked } from '../types/settings'

const DEFAULT_SETTINGS: UserSettings = {
  api_keys: {},
  preferences: {
    default_data_source: 'auto',
    default_image_source: 'sentinel_hub',
    language: 'en',
  },
}

interface FieldSpec {
  field: APIKeyField
  label: string
  description: string
  secret: boolean
  /**
   * Service to validate against, if any.
   *
   * `gee_project_id` has none: it is a Google Cloud project identifier, not a
   * credential, and the backend has never had a `gee` validator - the old
   * Verify button on it returned 400 on every click.
   */
  service?: ValidatableService
  /** Field holding the second half of a credential pair (Sentinel Hub). */
  pairedWith?: APIKeyField
  helpUrl: string
}

const FIELDS: FieldSpec[] = [
  {
    field: 'sentinel_hub_client_id',
    label: 'Sentinel Hub Client ID',
    description: 'Elevation and Sentinel-2 imagery. Free tier: 30,000 processing units/month.',
    secret: false,
    service: 'sentinel_hub',
    pairedWith: 'sentinel_hub_client_secret',
    helpUrl: 'https://apps.sentinel-hub.com/',
  },
  {
    field: 'sentinel_hub_client_secret',
    label: 'Sentinel Hub Client Secret',
    description: 'Second half of the OAuth2 credential pair. Verified together with the Client ID.',
    secret: true,
    service: 'sentinel_hub',
    pairedWith: 'sentinel_hub_client_id',
    helpUrl: 'https://apps.sentinel-hub.com/',
  },
  {
    field: 'opentopography_api_key',
    label: 'OpenTopography API Key',
    description: 'Global elevation data (Copernicus, SRTM, NASADEM). Free key, elevation only.',
    secret: true,
    service: 'opentopography',
    helpUrl: 'https://opentopography.org/',
  },
  {
    field: 'azure_maps_subscription_key',
    label: 'Azure Maps Subscription Key',
    description: 'Aerial imagery only, no elevation. Free tier: 1,000 transactions/day.',
    secret: true,
    service: 'azure_maps',
    helpUrl: 'https://azure.microsoft.com/products/azure-maps/',
  },
  {
    field: 'gee_project_id',
    label: 'Google Earth Engine Project ID',
    description: 'Optional. Requires a Google Cloud service account key on the server.',
    secret: false,
    helpUrl: 'https://developers.google.com/earth-engine/guides/service_account',
  },
]

type ValidationState = Record<string, ValidationResult | 'pending' | undefined>

export const SettingsPage = () => {
  const { i18n, t } = useTranslation()

  const [saved, setSaved] = useState<UserSettings>(DEFAULT_SETTINGS)
  const [edits, setEdits] = useState<APIKeys>({})
  const [preferences, setPreferences] = useState(DEFAULT_SETTINGS.preferences)
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({})
  const [validation, setValidation] = useState<ValidationState>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const settings = await getSettings()
      setSaved(settings)
      setPreferences(settings.preferences)
      setEdits({})
      setValidation({})
      setMessage(null)
    } catch (error) {
      setMessage({
        kind: 'error',
        text: error instanceof Error ? error.message : 'Failed to load settings',
      })
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  /**
   * Current value of a field.
   *
   * Masked placeholders are never put in the input. Showing `***abcd` as an
   * editable value makes "configured" indistinguishable from a key that
   * literally reads `***abcd`, and sending it back for validation can only
   * fail. The input stays empty and a "configured" badge is shown instead.
   */
  const valueOf = (field: APIKeyField): string => {
    if (field in edits) {
      return edits[field] ?? ''
    }
    const stored = saved.api_keys[field]
    return isMasked(stored) ? '' : (stored ?? '')
  }

  const isConfigured = (field: APIKeyField): boolean => {
    const stored = saved.api_keys[field]
    return Boolean(stored) && !(field in edits)
  }

  const handleChange = (field: APIKeyField, value: string) => {
    setEdits((prev) => ({ ...prev, [field]: value }))
    setValidation((prev) => ({ ...prev, [field]: undefined }))
  }

  const handleValidate = async (spec: FieldSpec) => {
    if (!spec.service) {
      return
    }

    const primary = spec.pairedWith && spec.field.endsWith('_secret') ? spec.pairedWith : spec.field
    const secondary = spec.pairedWith && spec.field.endsWith('_secret') ? spec.field : spec.pairedWith

    const apiKey = valueOf(primary)
    const apiSecret = secondary ? valueOf(secondary) : undefined

    if (!apiKey) {
      setValidation((prev) => ({
        ...prev,
        [spec.field]: { valid: false, error: 'Enter the Client ID first' },
      }))
      return
    }
    if (secondary && !apiSecret) {
      setValidation((prev) => ({
        ...prev,
        [spec.field]: { valid: false, error: 'Enter both the Client ID and the Client Secret' },
      }))
      return
    }

    setValidation((prev) => ({ ...prev, [spec.field]: 'pending' }))

    try {
      const result = await validateCredential(spec.service, apiKey, apiSecret)
      // Sentinel Hub is one credential: reflect the verdict on both inputs.
      setValidation((prev) => ({
        ...prev,
        [spec.field]: result,
        ...(spec.pairedWith ? { [spec.pairedWith]: result } : {}),
      }))
    } catch (error) {
      setValidation((prev) => ({
        ...prev,
        [spec.field]: {
          valid: false,
          error: error instanceof Error ? error.message : 'Validation failed',
        },
      }))
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    setMessage(null)
    try {
      // Only changed keys are sent. Untouched fields keep their stored value
      // server-side, so a preferences-only edit cannot disturb credentials.
      const updated = await saveSettings({
        ...(Object.keys(edits).length > 0 ? { api_keys: edits } : {}),
        preferences,
      })
      setSaved(updated)
      setPreferences(updated.preferences)
      setEdits({})
      setMessage({ kind: 'success', text: 'Settings saved' })

      if (updated.preferences.language !== i18n.language) {
        void i18n.changeLanguage(updated.preferences.language)
      }
    } catch (error) {
      setMessage({
        kind: 'error',
        text: error instanceof Error ? error.message : 'Failed to save settings',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const hasChanges = useMemo(
    () =>
      Object.keys(edits).length > 0 ||
      JSON.stringify(preferences) !== JSON.stringify(saved.preferences),
    [edits, preferences, saved.preferences],
  )

  return (
    <div className="flex-1 overflow-y-auto bg-gray-900 py-8">
      <div className="max-w-3xl mx-auto px-4 space-y-6">
        <header>
          <div className="flex items-center gap-3 mb-2">
            <Settings size={28} className="text-primary-400" />
            <h1 className="text-2xl font-bold text-white">{t('settings.title')}</h1>
          </div>
          <p className="text-sm text-gray-400">
            Keys are encrypted before being written to disk and are never returned in full.
          </p>
        </header>

        {message && (
          <div
            role="status"
            className={`p-4 rounded-lg text-sm ${
              message.kind === 'success'
                ? 'bg-green-900/40 text-green-200 border border-green-700'
                : 'bg-red-900/40 text-red-200 border border-red-700'
            }`}
          >
            {message.text}
          </div>
        )}

        <section className="bg-gray-800 rounded-lg p-6 space-y-4 border border-gray-700">
          <h2 className="text-lg font-bold text-white">API Keys</h2>
          <p className="text-sm text-gray-400">
            At least one elevation source is required: OpenTopography or Sentinel Hub.
          </p>

          {isLoading ? (
            <div className="flex items-center gap-2 text-gray-400 py-6">
              <Loader2 className="w-4 h-4 animate-spin" />
              {t('common.loading')}
            </div>
          ) : (
            FIELDS.map((spec) => {
              const state = validation[spec.field]
              const pending = state === 'pending'
              const result = state === 'pending' ? undefined : state
              const configured = isConfigured(spec.field)

              return (
                <div
                  key={spec.field}
                  className="border border-gray-700 rounded-lg p-4 bg-gray-800/60"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1">
                      <label
                        htmlFor={spec.field}
                        className="block text-sm font-semibold text-gray-200 mb-1"
                      >
                        {spec.label}
                        {configured && (
                          <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-green-900/60 text-green-300 border border-green-700">
                            configured
                          </span>
                        )}
                      </label>
                      <p className="text-xs text-gray-500">{spec.description}</p>
                    </div>
                    {result &&
                      (result.valid ? (
                        <Check className="text-green-400 flex-shrink-0" size={20} />
                      ) : (
                        <X className="text-red-400 flex-shrink-0" size={20} />
                      ))}
                  </div>

                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <input
                        id={spec.field}
                        type={spec.secret && !showSecret[spec.field] ? 'password' : 'text'}
                        value={valueOf(spec.field)}
                        onChange={(event) => handleChange(spec.field, event.target.value)}
                        placeholder={configured ? 'Stored - type to replace' : `Enter ${spec.label}`}
                        autoComplete="off"
                        spellCheck={false}
                        className="w-full px-3 py-2 pr-9 bg-gray-900 border border-gray-600 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                      {spec.secret && (
                        <button
                          type="button"
                          onClick={() =>
                            setShowSecret((prev) => ({
                              ...prev,
                              [spec.field]: !prev[spec.field],
                            }))
                          }
                          aria-label={showSecret[spec.field] ? 'Hide value' : 'Show value'}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                        >
                          {showSecret[spec.field] ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      )}
                    </div>

                    {spec.service && (
                      <button
                        type="button"
                        onClick={() => handleValidate(spec)}
                        disabled={pending || !valueOf(spec.field)}
                        className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed flex items-center gap-2 text-sm"
                      >
                        {pending ? <Loader2 size={14} className="animate-spin" /> : null}
                        Verify
                      </button>
                    )}
                  </div>

                  {result?.message && (
                    <p className="mt-2 text-sm text-green-400">{result.message}</p>
                  )}
                  {result?.error && <p className="mt-2 text-sm text-red-400">{result.error}</p>}

                  <a
                    href={spec.helpUrl}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="mt-2 inline-flex items-center gap-1 text-xs text-primary-400 hover:underline"
                  >
                    <Info size={12} />
                    Where to get this
                  </a>
                </div>
              )
            })
          )}
        </section>

        <section className="bg-gray-800 rounded-lg p-6 space-y-4 border border-gray-700">
          <h2 className="text-lg font-bold text-white">Preferences</h2>

          <div>
            <label
              htmlFor="default-data-source"
              className="block text-sm font-semibold text-gray-300 mb-2"
            >
              Default elevation source
            </label>
            <select
              id="default-data-source"
              value={preferences.default_data_source}
              onChange={(event) =>
                setPreferences((prev) => ({ ...prev, default_data_source: event.target.value }))
              }
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="auto">Auto (best available)</option>
              <option value="opentopography">OpenTopography</option>
              <option value="sentinel_hub">Sentinel Hub</option>
              <option value="google_earth_engine">Google Earth Engine</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="default-image-source"
              className="block text-sm font-semibold text-gray-300 mb-2"
            >
              Default imagery source
            </label>
            <select
              id="default-image-source"
              value={preferences.default_image_source}
              onChange={(event) =>
                setPreferences((prev) => ({ ...prev, default_image_source: event.target.value }))
              }
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="sentinel_hub">Sentinel Hub</option>
              <option value="azure_maps">Azure Maps</option>
            </select>
          </div>

          <div>
            <label htmlFor="language" className="block text-sm font-semibold text-gray-300 mb-2">
              Language
            </label>
            <select
              id="language"
              value={preferences.language}
              onChange={(event) =>
                setPreferences((prev) => ({ ...prev, language: event.target.value }))
              }
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="en">English</option>
              <option value="ru">Русский</option>
            </select>
          </div>
        </section>

        <div className="flex justify-end gap-3 pb-8">
          <button
            type="button"
            onClick={() => void load()}
            disabled={isLoading || isSaving}
            className="px-5 py-2.5 bg-gray-700 text-gray-200 rounded-md hover:bg-gray-600 disabled:opacity-50 font-medium"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={isSaving || isLoading || !hasChanges}
            className="px-5 py-2.5 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-700 disabled:text-gray-500 font-medium flex items-center gap-2"
          >
            {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}

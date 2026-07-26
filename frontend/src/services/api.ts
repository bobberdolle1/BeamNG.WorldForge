/**
 * API client for the BeamNG.WorldForge backend.
 */

import axios, { AxiosError } from 'axios'
import type {
  CredentialValidationResult,
  DataSourcesResponse,
  GenerationStatus,
  MapGenerationRequest,
  MapGenerationResponse,
} from '../types'
import type { UserSettings, ValidatableService } from '../types/settings'

/**
 * Shared axios instance.
 *
 * Exported so tests can attach a mock adapter to exactly the instance the app
 * uses, rather than stubbing the module and losing the interceptor behaviour
 * under test.
 */
export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  // Without a timeout axios waits forever, so a hung backend leaves the UI
  // spinning with no way to recover short of a page reload.
  timeout: 30_000,
})

/**
 * An API failure with a message worth showing to the user.
 *
 * Errors used to surface as `err.message` ("Request failed with status code
 * 422"), which told the user nothing. The backend puts a human-readable reason
 * in `detail`; this class makes sure that reason is what reaches the UI.
 */
export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>

    if (axiosError.code === 'ECONNABORTED') {
      return new ApiError('The server took too long to respond. Please try again.')
    }
    if (!axiosError.response) {
      return new ApiError('Cannot reach the server. Is the backend running?')
    }

    const detail = axiosError.response.data?.detail
    return new ApiError(
      typeof detail === 'string' && detail ? detail : axiosError.message,
      axiosError.response.status,
    )
  }

  return new ApiError(error instanceof Error ? error.message : 'Unexpected error')
}

async function request<T>(operation: () => Promise<{ data: T }>): Promise<T> {
  try {
    return (await operation()).data
  } catch (error) {
    throw toApiError(error)
  }
}

/** Start map generation. Resolves as soon as the job is queued. */
export function generateMap(payload: MapGenerationRequest): Promise<MapGenerationResponse> {
  return request(() => api.post<MapGenerationResponse>('/generate', payload))
}

/** Get the current state of a generation job. */
export function getGenerationStatus(jobId: string): Promise<GenerationStatus> {
  return request(() => api.get<GenerationStatus>(`/status/${jobId}`))
}

/** List the data sources the server knows about, with availability. */
export function getDataSources(): Promise<DataSourcesResponse> {
  return request(() => api.get<DataSourcesResponse>('/data-sources'))
}

/** Delete a finished job and the files it produced. */
export function deleteJob(jobId: string): Promise<void> {
  return request(() => api.delete(`/jobs/${jobId}`)).then(() => undefined)
}

/** Load stored settings. Secrets come back masked. */
export function getSettings(): Promise<UserSettings> {
  return request(() => api.get<UserSettings>('/settings'))
}

/**
 * Persist settings.
 *
 * Partial updates are supported: fields left out are preserved, and masked
 * placeholders are discarded server-side rather than saved over real keys.
 */
export function saveSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  return request(() => api.put<UserSettings>('/settings', settings))
}

/** Validate a provider credential without storing it. */
export function validateCredential(
  service: ValidatableService,
  apiKey: string,
  apiSecret?: string,
): Promise<CredentialValidationResult> {
  // Credentials go in the body, never the query string - query strings are
  // recorded in access logs, proxies and browser history.
  return request(() =>
    api.post<CredentialValidationResult>(`/settings/validate/${service}`, {
      api_key: apiKey,
      api_secret: apiSecret,
    }),
  )
}

/** Server health and job counters. */
export function checkHealth(): Promise<Record<string, unknown>> {
  return request(() => api.get<Record<string, unknown>>('/health'))
}

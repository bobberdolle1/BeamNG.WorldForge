/**
 * Type definitions for BeamNG.WorldForge.
 *
 * These mirror the backend's pydantic models. Keep them in sync with
 * `backend/models/map_request.py` - the API is the source of truth.
 */

export interface BoundingBox {
  min_lat: number
  max_lat: number
  min_lon: number
  max_lon: number
}

export type DataSourceId =
  | 'auto'
  | 'sentinel_hub'
  | 'opentopography'
  | 'bing_maps'
  | 'azure_maps'
  | 'google_earth_engine'

export interface MapGenerationRequest {
  name: string
  bbox: BoundingBox
  resolution?: number
  /** Must be a power of two between 256 and 4096; the backend rejects anything else. */
  heightmap_size?: number
  data_source?: DataSourceId
  use_ai_segmentation?: boolean
}

export interface MapGenerationResponse {
  success: boolean
  message: string
  map_id?: string
  /** The slug the backend derived from the submitted name. */
  map_name?: string
  download_url?: string
  preview_url?: string
  error?: string
}

/**
 * Job lifecycle states, matching `services/jobs.py::JobStatus`.
 *
 * The frontend previously declared a `'starting'` state that the backend never
 * emits, so the initial optimistic status never matched a real server state.
 */
export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'

export const TERMINAL_STATUSES: readonly JobStatus[] = ['completed', 'failed', 'cancelled']

export function isTerminal(status: JobStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}

/** Free-form extras the backend attaches to a job (feature counts, timings, ...). */
export interface JobStats {
  data_source?: string
  ai_enabled?: boolean
  ai_error?: string
  roads?: number
  buildings?: number
  archive_size_mb?: number
  dem_resolution_m?: number
  terrain?: {
    width: number
    height: number
    min_elevation: number
    max_elevation: number
    elevation_range: number
    nodata_fraction: number
  }
}

export interface GenerationStatus {
  job_id: string
  status: JobStatus
  progress: number
  message: string
  map_name?: string
  error?: string | null
  download_url?: string
  preview_url?: string
  stats?: JobStats | null
  created_at?: number
  updated_at?: number
}

export type Capability = 'dem' | 'imagery'

export interface DataSource {
  id: string
  name: string
  description: string
  available: boolean
  requires_setup: boolean
  recommended: boolean
  deprecated?: boolean
  provides?: Capability[]
}

export interface DataSourcesResponse {
  sources: DataSource[]
  default: string | null
  message: string
}

export interface CredentialValidationResult {
  valid: boolean
  message?: string
  error?: string
}

/** A detected road, as produced by the vector extraction stage. */
export interface RoadFeature {
  /** Polyline of [latitude, longitude] pairs. */
  centerline: [number, number][]
  width: number
  type: string
}

/** A detected building footprint. */
export interface BuildingFeature {
  /** Polygon of [latitude, longitude] pairs. */
  footprint: [number, number][]
  height: number
  type: string
}

/** Geographic extent used by the 3D preview components. */
export interface MapBounds {
  minLat: number
  maxLat: number
  minLon: number
  maxLon: number
}

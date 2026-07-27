/**
 * Geometry helpers for the map area selector.
 *
 * The equirectangular approximation here matches `bbox_dimensions` on the
 * backend: latitude uses a fixed metres-per-degree, longitude scales it by the
 * cosine of the centre latitude. Keeping the two in step matters because the
 * backend rejects a request whose area falls outside MIN/MAX, and a selector
 * that measured differently would let the user draw a box the API then refuses.
 */

import type { BoundingBox } from '../types'

/** Metres per degree of latitude, as used by the backend. */
const METERS_PER_DEGREE_LAT = 111_320

/** Mirrors MAX_AREA_KM2 in backend/models/map_request.py. */
const MAX_AREA_KM2 = 400

/** Mirrors MIN_AREA_KM2 in backend/models/map_request.py. */
const MIN_AREA_KM2 = 0.01

/** Number of cells the overlay grid divides the selection into, per axis. */
const GRID_DIVISIONS = 4

/** A point as Leaflet reports it. */
export interface LatLng {
  lat: number
  lng: number
}

/** A `[latitude, longitude]` pair, the order Leaflet expects. */
export type LatLonTuple = [number, number]

export interface Measurement {
  widthKm: number
  heightKm: number
  areaKm2: number
  /** True when the box exceeds what the backend accepts. */
  tooLarge: boolean
}

/** Metres per degree of longitude at a given latitude, guarded near the poles. */
function metersPerDegreeLon(latitude: number): number {
  const scale = Math.cos((latitude * Math.PI) / 180)
  return METERS_PER_DEGREE_LAT * Math.max(scale, 1e-6)
}

/** Physical size of a box, and whether it is within the backend's limit. */
export function measure(bbox: BoundingBox): Measurement {
  const centerLat = (bbox.min_lat + bbox.max_lat) / 2
  const widthKm =
    (Math.abs(bbox.max_lon - bbox.min_lon) * metersPerDegreeLon(centerLat)) / 1000
  const heightKm = (Math.abs(bbox.max_lat - bbox.min_lat) * METERS_PER_DEGREE_LAT) / 1000
  const areaKm2 = widthKm * heightKm

  return { widthKm, heightKm, areaKm2, tooLarge: areaKm2 > MAX_AREA_KM2 }
}

/**
 * Build a square selection anchored at `start` and extending towards `current`.
 *
 * BeamNG terrains are square, so the selector always produces a square region
 * measured in metres rather than in degrees - away from the equator a box with
 * equal degree spans is visibly oblong on the ground. The longer axis of the
 * drag sets the side length, and the drag direction sets which way it grows.
 *
 * Returns `null` for a gesture too small to be deliberate (a click, or a drag
 * of a few pixels), which the backend would reject as below MIN_AREA_KM2.
 */
export function squareBoundsFrom(start: LatLng, current: LatLng): BoundingBox | null {
  const centerLat = (start.lat + current.lat) / 2
  const lonMetersPerDegree = metersPerDegreeLon(centerLat)

  const latMeters = (current.lat - start.lat) * METERS_PER_DEGREE_LAT
  const lonMeters = (current.lng - start.lng) * lonMetersPerDegree
  const sideMeters = Math.max(Math.abs(latMeters), Math.abs(lonMeters))

  if ((sideMeters * sideMeters) / 1_000_000 < MIN_AREA_KM2) {
    return null
  }

  const latSpan = sideMeters / METERS_PER_DEGREE_LAT
  const lonSpan = sideMeters / lonMetersPerDegree
  const endLat = start.lat + (current.lat >= start.lat ? latSpan : -latSpan)
  const endLon = start.lng + (current.lng >= start.lng ? lonSpan : -lonSpan)

  return {
    min_lat: Math.max(Math.min(start.lat, endLat), -90),
    max_lat: Math.min(Math.max(start.lat, endLat), 90),
    min_lon: Math.max(Math.min(start.lng, endLon), -180),
    max_lon: Math.min(Math.max(start.lng, endLon), 180),
  }
}

/** Convert a box to the corner pair Leaflet's `bounds` prop expects. */
export function toLeafletBounds(bbox: BoundingBox): [LatLonTuple, LatLonTuple] {
  return [
    [bbox.min_lat, bbox.min_lon],
    [bbox.max_lat, bbox.max_lon],
  ]
}

/**
 * Interior grid lines for the selection overlay.
 *
 * Each entry is a polyline; the grid gives the drawn box a sense of scale
 * without needing a separate tile layer.
 */
export function gridLines(bbox: BoundingBox, divisions = GRID_DIVISIONS): LatLonTuple[][] {
  const lines: LatLonTuple[][] = []

  for (let step = 1; step < divisions; step += 1) {
    const fraction = step / divisions

    const lat = bbox.min_lat + (bbox.max_lat - bbox.min_lat) * fraction
    lines.push([
      [lat, bbox.min_lon],
      [lat, bbox.max_lon],
    ])

    const lon = bbox.min_lon + (bbox.max_lon - bbox.min_lon) * fraction
    lines.push([
      [bbox.min_lat, lon],
      [bbox.max_lat, lon],
    ])
  }

  return lines
}

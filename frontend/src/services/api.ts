/**
 * API client for BeamNG.WorldForge backend
 */

import axios from 'axios'
import { MapGenerationRequest, MapGenerationResponse, GenerationStatus } from '../types'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Start map generation
 */
export async function generateMap(request: MapGenerationRequest): Promise<MapGenerationResponse> {
  const response = await api.post<MapGenerationResponse>('/generate', request)
  return response.data
}

/**
 * Get generation status
 */
export async function getGenerationStatus(jobId: string): Promise<GenerationStatus> {
  const response = await api.get<GenerationStatus>(`/status/${jobId}`)
  return response.data
}

/**
 * Health check
 */
export async function checkHealth(): Promise<any> {
  const response = await api.get('/health')
  return response.data
}


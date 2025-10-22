/**
 * Type definitions for BeamNG.WorldForge
 */

export interface BoundingBox {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
}

export interface MapGenerationRequest {
  name: string;
  bbox: BoundingBox;
  resolution?: number;
  heightmap_size?: number;
  data_source?: 'auto' | 'sentinel_hub' | 'opentopography' | 'bing_maps' | 'azure_maps' | 'google_earth_engine';
  use_ai_segmentation?: boolean;  // Этап 2: AI features
}

export interface MapGenerationResponse {
  success: boolean;
  message: string;
  map_id?: string;
  download_url?: string;
  preview_url?: string;
  error?: string;
}

export interface AIStats {
  roads: number;
  buildings: number;
}

export interface GenerationStatus {
  job_id: string;
  status: 'starting' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  error?: string;
  download_url?: string;
  preview_url?: string;
  ai_stats?: AIStats | null;  // Этап 2: AI statistics
}

export interface DataSource {
  id: string;
  name: string;
  description: string;
  available: boolean;
  requires_setup: boolean;
  recommended: boolean;
}

export interface DataSourcesResponse {
  sources: DataSource[];
  default: string | null;
  message: string;
}


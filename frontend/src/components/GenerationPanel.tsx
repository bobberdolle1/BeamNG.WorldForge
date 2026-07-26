import { CheckCircle, Database, Download, Eye, Image as ImageIcon, Loader2, Play, XCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useGenerationJob } from '../hooks/useGenerationJob'
import { computeStageProgress } from '../lib/stages'
import { getDataSources } from '../services/api'
import type { BoundingBox, DataSource, DataSourceId, GenerationStatus } from '../types'
import { PreviewPanel } from './PreviewPanel'
import { ProgressIndicator } from './ProgressIndicator'

/** Heightmap sizes BeamNG accepts (power of two). */
const HEIGHTMAP_SIZES = [512, 1024, 2048, 4096] as const

/** Matches MAX_AREA_KM2 in backend/models/map_request.py. */
const MAX_AREA_KM2 = 400

interface GenerationPanelProps {
  selectedBBox: BoundingBox | null
  onStatusChange?: (status: GenerationStatus | null) => void
}

/** Approximate the area of a bbox, mirroring the backend's equirectangular estimate. */
function areaKm2(bbox: BoundingBox): number {
  const metersPerDegreeLat = 111_320
  const centerLat = (bbox.min_lat + bbox.max_lat) / 2
  const metersPerDegreeLon = metersPerDegreeLat * Math.cos((centerLat * Math.PI) / 180)

  const width = Math.abs(bbox.max_lon - bbox.min_lon) * metersPerDegreeLon
  const height = Math.abs(bbox.max_lat - bbox.min_lat) * metersPerDegreeLat
  return (width * height) / 1_000_000
}

export default function GenerationPanel({ selectedBBox, onStatusChange }: GenerationPanelProps) {
  const { t } = useTranslation()

  const [mapName, setMapName] = useState('')
  const [resolution, setResolution] = useState(30)
  const [heightmapSize, setHeightmapSize] = useState<number>(1024)
  const [dataSource, setDataSource] = useState<DataSourceId>('auto')
  const [availableSources, setAvailableSources] = useState<DataSource[]>([])
  const [sourcesError, setSourcesError] = useState<string | null>(null)
  const [useAI, setUseAI] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  const { status, error, isBusy, start, reset } = useGenerationJob()

  useEffect(() => {
    onStatusChange?.(status)
  }, [status, onStatusChange])

  useEffect(() => {
    let cancelled = false

    getDataSources()
      .then((data) => {
        if (!cancelled) {
          setAvailableSources(data.sources)
          setSourcesError(null)
        }
      })
      .catch((caught: Error) => {
        // Surfaced in the UI rather than only console.error'd: an empty picker
        // with no explanation looked like the app was broken.
        if (!cancelled) {
          setSourcesError(caught.message)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const selectedArea = useMemo(
    () => (selectedBBox ? areaKm2(selectedBBox) : 0),
    [selectedBBox],
  )

  const areaTooLarge = selectedArea > MAX_AREA_KM2

  const steps = useMemo(
    () => computeStageProgress(status?.progress ?? 0, useAI, status?.status === 'failed'),
    [status?.progress, status?.status, useAI],
  )

  const handleGenerate = async () => {
    setValidationError(null)

    if (!selectedBBox) {
      setValidationError(t('generation.selectRegionFirst'))
      return
    }
    if (!mapName.trim()) {
      setValidationError(t('generation.enterMapName'))
      return
    }
    if (areaTooLarge) {
      setValidationError(`${t('generation.areaTooLarge')} (${selectedArea.toFixed(1)} km²)`)
      return
    }

    // The backend slugifies the name itself; send it as typed so its rules stay
    // the single source of truth.
    await start({
      name: mapName.trim(),
      bbox: selectedBBox,
      resolution,
      heightmap_size: heightmapSize,
      data_source: dataSource,
      use_ai_segmentation: useAI,
    })
  }

  const displayedError = validationError ?? error ?? null
  const isCompleted = status?.status === 'completed'

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2">{t('generation.title')}</h2>
        <p className="text-sm text-gray-400">{t('generation.configure')}</p>
      </div>

      <div>
        <label htmlFor="map-name" className="block text-sm font-medium text-gray-300 mb-2">
          {t('generation.mapName')}
        </label>
        <input
          id="map-name"
          type="text"
          value={mapName}
          onChange={(event) => setMapName(event.target.value)}
          placeholder={t('generation.mapNamePlaceholder')}
          disabled={isBusy}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        />
      </div>

      {selectedBBox && (
        <div
          className={`p-3 rounded-lg ${areaTooLarge ? 'bg-red-900/40 border border-red-700' : 'bg-gray-700'}`}
        >
          <h3 className="text-sm font-semibold text-gray-300 mb-2">
            {t('generation.regionSize', { area: selectedArea.toFixed(2) })}
          </h3>
          <div className="text-xs text-gray-400 space-y-1">
            <div>
              Lat: {selectedBBox.min_lat.toFixed(4)} to {selectedBBox.max_lat.toFixed(4)}
            </div>
            <div>
              Lon: {selectedBBox.min_lon.toFixed(4)} to {selectedBBox.max_lon.toFixed(4)}
            </div>
          </div>
          {areaTooLarge && (
            <p className="mt-2 text-xs text-red-300">
              {t('generation.areaTooLarge')} — max {MAX_AREA_KM2} km²
            </p>
          )}
        </div>
      )}

      <div>
        <label htmlFor="resolution" className="block text-sm font-medium text-gray-300 mb-2">
          {t('generation.resolution')}: {resolution}m
        </label>
        <input
          id="resolution"
          type="range"
          min="10"
          max="100"
          step="10"
          value={resolution}
          onChange={(event) => setResolution(Number(event.target.value))}
          disabled={isBusy}
          className="w-full"
        />
      </div>

      <div>
        <label htmlFor="heightmap-size" className="block text-sm font-medium text-gray-300 mb-2">
          {t('generation.heightmapSize')}: {heightmapSize}×{heightmapSize}
        </label>
        <select
          id="heightmap-size"
          value={heightmapSize}
          onChange={(event) => setHeightmapSize(Number(event.target.value))}
          disabled={isBusy}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        >
          {HEIGHTMAP_SIZES.map((size) => (
            <option key={size} value={size}>
              {size}×{size}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-gray-700 p-4 rounded-lg border border-gray-600">
        <label htmlFor="data-source" className="block text-sm font-medium text-gray-300 mb-2">
          <Database className="w-4 h-4 inline mr-2" />
          {t('generation.dataSource')}
        </label>
        <select
          id="data-source"
          value={dataSource}
          onChange={(event) => setDataSource(event.target.value as DataSourceId)}
          disabled={isBusy}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 mb-2"
        >
          <option value="auto">🎯 Auto (best available)</option>
          {availableSources.map((source) => (
            <option key={source.id} value={source.id} disabled={!source.available}>
              {source.recommended ? '⭐ ' : ''}
              {source.name}
              {source.available ? '' : ` (${t('generation.dataSourceUnavailable')})`}
            </option>
          ))}
        </select>
        {sourcesError && <p className="text-xs text-red-400">{sourcesError}</p>}
        {!sourcesError && (
          <p className="text-xs text-gray-400">
            {availableSources.find((source) => source.id === dataSource)?.description.split('\n')[0] ??
              'Automatically selects the best configured source.'}
          </p>
        )}
      </div>

      <div className="bg-gradient-to-r from-purple-900 to-blue-900 p-4 rounded-lg border border-purple-700">
        <label className="flex items-center gap-2 text-sm font-medium text-white cursor-pointer">
          <input
            type="checkbox"
            checked={useAI}
            onChange={(event) => setUseAI(event.target.checked)}
            disabled={isBusy}
            className="w-5 h-5 rounded border-gray-600 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
          />
          🤖 {t('generation.aiSegmentation')}
        </label>
        <p className="text-xs text-gray-300 ml-7 mt-2">
          {/* Stated plainly: this needs a local Ollama install, and without one
              the run still succeeds but detects nothing. */}
          {t('generation.aiDescription')} — requires a local Ollama install.
        </p>
      </div>

      {displayedError && (
        <div className="bg-red-900 bg-opacity-50 border border-red-700 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-200">{displayedError}</p>
          </div>
        </div>
      )}

      {status && (
        <div className="bg-gray-700 p-4 rounded-lg space-y-3">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">{status.progress}%</h3>
            {status.status === 'processing' && (
              <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
            )}
            {isCompleted && <CheckCircle className="w-5 h-5 text-green-400" />}
            {status.status === 'failed' && <XCircle className="w-5 h-5 text-red-400" />}
          </div>

          <ProgressIndicator steps={steps} currentMessage={status.message} />

          {useAI && status.stats?.ai_enabled === false && (
            <p className="text-xs text-yellow-300">
              {t('generation.aiUnavailable')}
              {status.stats.ai_error ? `: ${status.stats.ai_error}` : ''}
            </p>
          )}

          {status.stats?.ai_enabled && (
            <div className="bg-purple-900 bg-opacity-30 p-3 rounded-lg border border-purple-700 grid grid-cols-2 gap-2 text-xs">
              <div>
                🛣️ {t('generation.results.roadsDetected', { count: status.stats.roads ?? 0 })}
              </div>
              <div>
                🏢 {t('generation.results.buildingsDetected', { count: status.stats.buildings ?? 0 })}
              </div>
            </div>
          )}

          {isCompleted && (
            <div className="space-y-2 pt-2">
              <a
                href={status.download_url}
                download
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                <Download className="w-4 h-4" />
                {t('generation.results.downloadMap')}
              </a>

              {status.preview_url && (
                <a
                  href={status.preview_url}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
                >
                  <ImageIcon className="w-4 h-4" />
                  {t('generation.results.viewPreview')}
                </a>
              )}

              <button
                type="button"
                onClick={() => setShowPreview(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                <Eye className="w-4 h-4" />
                {t('generation.results.preview3D')}
              </button>
            </div>
          )}

          {(isCompleted || status.status === 'failed') && (
            <button
              type="button"
              onClick={reset}
              className="w-full px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors"
            >
              {t('generation.startOver')}
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={handleGenerate}
        disabled={!selectedBBox || !mapName.trim() || isBusy || areaTooLarge}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
      >
        {isBusy ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            {t('generation.generating')}
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            {t('generation.generate')}
          </>
        )}
      </button>

      {isCompleted && (
        <PreviewPanel
          isOpen={showPreview}
          onClose={() => setShowPreview(false)}
          mapData={{
            heightmapUrl: status?.preview_url ?? '',
            roads: [],
            buildings: [],
            mapBounds: selectedBBox
              ? {
                  minLat: selectedBBox.min_lat,
                  maxLat: selectedBBox.max_lat,
                  minLon: selectedBBox.min_lon,
                  maxLon: selectedBBox.max_lon,
                }
              : undefined,
            mapSize: 100,
          }}
        />
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Download, Loader2, CheckCircle, XCircle, Play, Image as ImageIcon, Eye, Database } from 'lucide-react'
import { BoundingBox, GenerationStatus, MapGenerationRequest, DataSource } from '../types'
import { generateMap, getGenerationStatus, getDataSources } from '../services/api'
import { PreviewPanel } from './PreviewPanel'
import { ProgressIndicator } from './ProgressIndicator'

interface GenerationPanelProps {
  selectedBBox: BoundingBox | null
  generationStatus: GenerationStatus | null
  onGenerationStart: (status: GenerationStatus) => void
}

export default function GenerationPanel({
  selectedBBox,
  generationStatus,
  onGenerationStart,
}: GenerationPanelProps) {
  const [mapName, setMapName] = useState('')
  const [resolution, setResolution] = useState(30)
  const [heightmapSize, setHeightmapSize] = useState(1024)
  const [dataSource, setDataSource] = useState<string>('auto')
  const [availableSources, setAvailableSources] = useState<DataSource[]>([])
  const [useAI, setUseAI] = useState(true)  // Этап 2: AI toggle
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)  // Этап 4: 3D Preview

  // Fetch available data sources on mount
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const data = await getDataSources()
        setAvailableSources(data.sources)
      } catch (err) {
        console.error('Failed to fetch data sources:', err)
      }
    }
    fetchSources()
  }, [])

  // Poll for status updates
  useEffect(() => {
    if (!generationStatus || generationStatus.status === 'completed' || generationStatus.status === 'failed') {
      return
    }

    const interval = setInterval(async () => {
      try {
        const status = await getGenerationStatus(generationStatus.job_id)
        onGenerationStart(status)

        if (status.status === 'completed' || status.status === 'failed') {
          setIsGenerating(false)
          clearInterval(interval)
        }
      } catch (err) {
        console.error('Failed to get status:', err)
        setError('Failed to get generation status')
        setIsGenerating(false)
        clearInterval(interval)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [generationStatus, onGenerationStart])

  const handleGenerate = async () => {
    if (!selectedBBox) {
      setError('Please select a region on the map first')
      return
    }

    if (!mapName.trim()) {
      setError('Please enter a map name')
      return
    }

    setError(null)
    setIsGenerating(true)

    try {
      const request: MapGenerationRequest = {
        name: mapName.trim().toLowerCase().replace(/\s+/g, '_'),
        bbox: selectedBBox,
        resolution,
        heightmap_size: heightmapSize,
        data_source: dataSource as any,
        use_ai_segmentation: useAI,  // Этап 2: включаем AI
      }

      const response = await generateMap(request)

      if (response.success && response.map_id) {
        onGenerationStart({
          job_id: response.map_id,
          status: 'starting',
          progress: 0,
          message: response.message,
        })
      } else {
        throw new Error(response.error || 'Failed to start generation')
      }
    } catch (err: any) {
      console.error('Generation failed:', err)
      setError(err.message || 'Failed to start map generation')
      setIsGenerating(false)
    }
  }

  const handleDownload = () => {
    if (generationStatus?.download_url) {
      window.open(generationStatus.download_url, '_blank')
    }
  }

  const handleViewPreview = () => {
    if (generationStatus?.preview_url) {
      window.open(generationStatus.preview_url, '_blank')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2">Map Configuration</h2>
        <p className="text-sm text-gray-400">
          Configure your map settings and generate
        </p>
      </div>

      {/* Map Name */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Map Name
        </label>
        <input
          type="text"
          value={mapName}
          onChange={(e) => setMapName(e.target.value)}
          placeholder="e.g., san_francisco_downtown"
          disabled={isGenerating}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        />
      </div>

      {/* Selected Region Info */}
      {selectedBBox && (
        <div className="bg-gray-700 p-3 rounded-lg">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">Selected Region</h3>
          <div className="text-xs text-gray-400 space-y-1">
            <div>Lat: {selectedBBox.min_lat.toFixed(4)} to {selectedBBox.max_lat.toFixed(4)}</div>
            <div>Lon: {selectedBBox.min_lon.toFixed(4)} to {selectedBBox.max_lon.toFixed(4)}</div>
          </div>
        </div>
      )}

      {/* Resolution */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          DEM Resolution: {resolution}m
        </label>
        <input
          type="range"
          min="10"
          max="100"
          step="10"
          value={resolution}
          onChange={(e) => setResolution(Number(e.target.value))}
          disabled={isGenerating}
          className="w-full"
        />
        <p className="text-xs text-gray-500 mt-1">
          Lower = more detail, slower download
        </p>
      </div>

      {/* Heightmap Size */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Heightmap Size: {heightmapSize}x{heightmapSize}
        </label>
        <select
          value={heightmapSize}
          onChange={(e) => setHeightmapSize(Number(e.target.value))}
          disabled={isGenerating}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        >
          <option value={512}>512x512</option>
          <option value={1024}>1024x1024</option>
          <option value={2048}>2048x2048</option>
          <option value={4096}>4096x4096</option>
        </select>
      </div>

      {/* Data Source Selector */}
      <div className="bg-gray-700 p-4 rounded-lg border border-gray-600">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Database className="w-4 h-4 inline mr-2" />
          Data Source
        </label>
        <select
          value={dataSource}
          onChange={(e) => setDataSource(e.target.value)}
          disabled={isGenerating}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 mb-2"
        >
          <option value="auto">🎯 Auto (Best Available)</option>
          {availableSources.map((source) => (
            <option 
              key={source.id} 
              value={source.id}
              disabled={!source.available}
            >
              {source.recommended ? '⭐ ' : ''}
              {source.name}
              {!source.available ? ' (Not Available)' : ''}
              {source.requires_setup ? ' ⚙️' : ' ✅'}
            </option>
          ))}
        </select>
        {availableSources.find(s => s.id === dataSource) && (
          <p className="text-xs text-gray-400">
            {availableSources.find(s => s.id === dataSource)?.description.split('\n')[0]}
          </p>
        )}
        {dataSource === 'auto' && (
          <p className="text-xs text-gray-400">
            Automatically selects best available free data source (Sentinel Hub or OpenTopography)
          </p>
        )}
      </div>

      {/* AI Segmentation Toggle - Этап 2 */}
      <div className="bg-gradient-to-r from-purple-900 to-blue-900 p-4 rounded-lg border border-purple-700">
        <div className="flex items-center justify-between mb-2">
          <label className="flex items-center gap-2 text-sm font-medium text-white cursor-pointer">
            <input
              type="checkbox"
              checked={useAI}
              onChange={(e) => setUseAI(e.target.checked)}
              disabled={isGenerating}
              className="w-5 h-5 rounded border-gray-600 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
            />
            <span className="flex items-center gap-2">
              🤖 AI-Powered Segmentation
              <span className="px-2 py-0.5 bg-purple-600 text-xs rounded-full">ЭТАП 2</span>
            </span>
          </label>
        </div>
        <p className="text-xs text-gray-300 ml-7">
          {useAI 
            ? '✨ AI will detect roads, buildings, water & forests' 
            : 'Basic terrain generation only'}
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900 bg-opacity-50 border border-red-700 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-200">{error}</p>
          </div>
        </div>
      )}

      {/* Generation Status */}
      {generationStatus && (
        <div className="bg-gray-700 p-4 rounded-lg space-y-3">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Generation Progress</h3>
            {generationStatus.status === 'processing' && (
              <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
            )}
            {generationStatus.status === 'completed' && (
              <CheckCircle className="w-5 h-5 text-green-400" />
            )}
            {generationStatus.status === 'failed' && (
              <XCircle className="w-5 h-5 text-red-400" />
            )}
          </div>

          {/* Detailed Progress Steps */}
          <ProgressIndicator
            steps={[
              {
                id: 'validate',
                status: generationStatus.progress >= 5 ? 'completed' : generationStatus.progress > 0 ? 'active' : 'pending',
                progress: generationStatus.progress < 10 ? generationStatus.progress * 10 : undefined
              },
              {
                id: 'fetch_dem',
                status: generationStatus.progress >= 20 ? 'completed' : generationStatus.progress >= 10 ? 'active' : 'pending',
                progress: generationStatus.progress >= 10 && generationStatus.progress < 20 ? (generationStatus.progress - 10) * 10 : undefined
              },
              {
                id: 'fetch_imagery',
                status: generationStatus.progress >= 35 ? 'completed' : generationStatus.progress >= 20 ? 'active' : 'pending',
                progress: generationStatus.progress >= 20 && generationStatus.progress < 35 ? ((generationStatus.progress - 20) / 15) * 100 : undefined
              },
              {
                id: 'process_terrain',
                status: generationStatus.progress >= 50 ? 'completed' : generationStatus.progress >= 35 ? 'active' : 'pending',
                progress: generationStatus.progress >= 35 && generationStatus.progress < 50 ? ((generationStatus.progress - 35) / 15) * 100 : undefined
              },
              ...(useAI ? [
                {
                  id: 'segment_features',
                  status: (generationStatus.progress >= 65 ? 'completed' : generationStatus.progress >= 50 ? 'active' : 'pending') as 'pending' | 'active' | 'completed' | 'error',
                  progress: generationStatus.progress >= 50 && generationStatus.progress < 65 ? ((generationStatus.progress - 50) / 15) * 100 : undefined
                },
                {
                  id: 'generate_roads',
                  status: (generationStatus.progress >= 75 ? 'completed' : generationStatus.progress >= 65 ? 'active' : 'pending') as 'pending' | 'active' | 'completed' | 'error',
                  progress: generationStatus.progress >= 65 && generationStatus.progress < 75 ? ((generationStatus.progress - 65) / 10) * 100 : undefined
                },
                {
                  id: 'generate_buildings',
                  status: (generationStatus.progress >= 85 ? 'completed' : generationStatus.progress >= 75 ? 'active' : 'pending') as 'pending' | 'active' | 'completed' | 'error',
                  progress: generationStatus.progress >= 75 && generationStatus.progress < 85 ? ((generationStatus.progress - 75) / 10) * 100 : undefined
                }
              ] : []),
              {
                id: 'generate_jbeam',
                status: (generationStatus.progress >= 95 ? 'completed' : generationStatus.progress >= (useAI ? 85 : 50) ? 'active' : 'pending') as 'pending' | 'active' | 'completed' | 'error',
                progress: generationStatus.progress >= (useAI ? 85 : 50) && generationStatus.progress < 95 ? ((generationStatus.progress - (useAI ? 85 : 50)) / (useAI ? 10 : 45)) * 100 : undefined
              },
              {
                id: 'package',
                status: (generationStatus.progress >= 100 ? 'completed' : generationStatus.progress >= 95 ? 'active' : 'pending') as 'pending' | 'active' | 'completed' | 'error',
                progress: generationStatus.progress >= 95 && generationStatus.progress < 100 ? (generationStatus.progress - 95) * 20 : undefined
              }
            ]}
            currentMessage={generationStatus.message}
          />

          {generationStatus.error && (
            <div className="mt-3 p-3 bg-red-900/30 border border-red-500/30 rounded-lg">
              <p className="text-xs text-red-400">{generationStatus.error}</p>
            </div>
          )}

          {/* AI Statistics - Этап 2 */}
          {generationStatus.ai_stats && generationStatus.status === 'completed' && (
            <div className="bg-purple-900 bg-opacity-30 p-3 rounded-lg border border-purple-700">
              <h4 className="text-xs font-semibold text-purple-300 mb-2">🤖 AI Detection Results</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span>🛣️ Roads:</span>
                  <span className="font-bold text-yellow-400">{generationStatus.ai_stats.roads}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span>🏢 Buildings:</span>
                  <span className="font-bold text-red-400">{generationStatus.ai_stats.buildings}</span>
                </div>
              </div>
            </div>
          )}

          {/* Download Button */}
          {generationStatus.status === 'completed' && (
            <div className="space-y-2 pt-2">
              <button
                onClick={handleDownload}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                <Download className="w-4 h-4" />
                Download Map (.zip)
              </button>
              
              {generationStatus.preview_url && (
                <button
                  onClick={handleViewPreview}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
                >
                  <ImageIcon className="w-4 h-4" />
                  View Preview
                </button>
              )}
              
              {/* 3D Preview Button - Этап 4 */}
              <button
                onClick={() => setShowPreview(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                <Eye className="w-4 h-4" />
                🎮 3D Preview
              </button>
            </div>
          )}
        </div>
      )}

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={!selectedBBox || !mapName.trim() || isGenerating}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            Generate Map
          </>
        )}
      </button>

      {/* Info */}
      <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-3">
        <p className="text-xs text-blue-200">
          <strong>Note:</strong> Generation may take 1-5 minutes depending on region size and resolution.
        </p>
      </div>
      
      {/* 3D Preview Modal - Этап 4 */}
      {generationStatus?.status === 'completed' && (
        <PreviewPanel
          isOpen={showPreview}
          onClose={() => setShowPreview(false)}
          mapData={{
            heightmapUrl: generationStatus.preview_url || '',
            roads: [], // TODO: load from API
            buildings: [], // TODO: load from API
            mapBounds: selectedBBox ? {
              minLat: selectedBBox.min_lat,
              maxLat: selectedBBox.max_lat,
              minLon: selectedBBox.min_lon,
              maxLon: selectedBBox.max_lon,
            } : undefined,
            mapSize: 100,
          }}
        />
      )}
    </div>
  )
}


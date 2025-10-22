import { useRef, useState } from 'react'
import { MapContainer, TileLayer, Rectangle, Polyline, useMapEvents } from 'react-leaflet'
import { LatLngBounds, LatLng } from 'leaflet'
import { BoundingBox } from '../types'
import { Layers, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import 'leaflet/dist/leaflet.css'

interface MapSelectorProps {
  onBBoxSelected: (bbox: BoundingBox) => void
  disabled?: boolean
}

// Calculate distance between two points in kilometers
function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371 // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  return R * c
}

function BBoxSelector({ onBBoxSelected, disabled, isSelectionMode }: MapSelectorProps & { isSelectionMode: boolean }) {
  const [bounds, setBounds] = useState<LatLngBounds | null>(null)
  const [gridLines, setGridLines] = useState<Array<[number, number][]>>([])
  const [isCreating, setIsCreating] = useState(false)
  const [startPoint, setStartPoint] = useState<LatLng | null>(null)

  useMapEvents({
    mousedown(e) {
      if (disabled || !isSelectionMode) return
      setIsCreating(true)
      setStartPoint(e.latlng)
      setBounds(null)
      setGridLines([])
    },
    mouseup(e) {
      if (disabled || !isSelectionMode || !isCreating || !startPoint) return
      setIsCreating(false)
      
      const latDiff = Math.abs(e.latlng.lat - startPoint.lat)
      const lonDiff = Math.abs(e.latlng.lng - startPoint.lng)
      const maxDiff = Math.max(latDiff, lonDiff)
      
      if (maxDiff < 0.001) {
        setStartPoint(null)
        return
      }
      
      const finalBounds = new LatLngBounds(
        [startPoint.lat, startPoint.lng],
        [
          startPoint.lat + (e.latlng.lat > startPoint.lat ? maxDiff : -maxDiff),
          startPoint.lng + (e.latlng.lng > startPoint.lng ? maxDiff : -maxDiff)
        ]
      )
      
      setBounds(finalBounds)
      generateGrid(finalBounds)
      
      const bbox: BoundingBox = {
        min_lat: finalBounds.getSouth(),
        max_lat: finalBounds.getNorth(),
        min_lon: finalBounds.getWest(),
        max_lon: finalBounds.getEast(),
      }
      
      onBBoxSelected(bbox)
      setStartPoint(null)
    },
    mousemove(e) {
      if (disabled || !startPoint || !isSelectionMode || !isCreating) return
      
      const latDiff = Math.abs(e.latlng.lat - startPoint.lat)
      const lonDiff = Math.abs(e.latlng.lng - startPoint.lng)
      const maxDiff = Math.max(latDiff, lonDiff)
      
      const previewBounds = new LatLngBounds(
        [startPoint.lat, startPoint.lng],
        [
          startPoint.lat + (e.latlng.lat > startPoint.lat ? maxDiff : -maxDiff),
          startPoint.lng + (e.latlng.lng > startPoint.lng ? maxDiff : -maxDiff)
        ]
      )
      
      setBounds(previewBounds)
      generateGrid(previewBounds)
    },
  })
  
  const generateGrid = (rectBounds: LatLngBounds) => {
    const south = rectBounds.getSouth()
    const north = rectBounds.getNorth()
    const west = rectBounds.getWest()
    const east = rectBounds.getEast()
    
    const latStep = (north - south) / 4
    const lonStep = (east - west) / 4
    
    const lines: Array<[number, number][]> = []
    
    for (let i = 1; i < 4; i++) {
      const lat = south + latStep * i
      lines.push([[lat, west], [lat, east]])
    }
    
    for (let i = 1; i < 4; i++) {
      const lon = west + lonStep * i
      lines.push([[south, lon], [north, lon]])
    }
    
    setGridLines(lines)
  }

  if (!bounds) return null

  // Calculate dimensions
  const width = calculateDistance(
    bounds.getSouth(), bounds.getWest(),
    bounds.getSouth(), bounds.getEast()
  )
  const height = calculateDistance(
    bounds.getSouth(), bounds.getWest(),
    bounds.getNorth(), bounds.getWest()
  )

  return (
    <>
      <Rectangle
        bounds={bounds}
        pathOptions={{
          color: isCreating ? '#10b981' : '#3b82f6',
          weight: 3,
          fillColor: isCreating ? '#34d399' : '#60a5fa',
          fillOpacity: isCreating ? 0.15 : 0.2,
          dashArray: undefined,
        }}
      />
      
      {/* Grid lines */}
      {gridLines.map((line, idx) => (
        <Polyline
          key={idx}
          positions={line as any}
          pathOptions={{
            color: isCreating ? '#6ee7b7' : '#93c5fd',
            weight: 1.5,
            opacity: isCreating ? 0.5 : 0.7,
            dashArray: '3, 3'
          }}
        />
      ))}
      
      {/* Size label overlay - top right with higher z-index */}
      {typeof window !== 'undefined' && (
        <div className="leaflet-top leaflet-right" style={{ marginTop: '80px', marginRight: '10px', zIndex: 1002 }}>
          <div className="bg-gradient-to-br from-blue-600 to-blue-700 text-white px-3 py-2 rounded-lg shadow-xl text-xs font-semibold border-2 border-blue-400/50 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <span className="text-base">📏</span>
              <div>
                <div className="font-bold">{width.toFixed(2)} × {height.toFixed(2)} km</div>
                <div className="text-[10px] opacity-80">{(width * height).toFixed(2)} km²</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default function MapSelector({ onBBoxSelected, disabled }: MapSelectorProps) {
  const { t } = useTranslation()
  const mapRef = useRef<any>(null)
  const [mapLayer, setMapLayer] = useState<'osm' | 'satellite' | 'topo' | 'hybrid'>('osm')
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [isSelectionMode, setIsSelectionMode] = useState(false)

  const layerUrls = {
    osm: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri'
    },
    topo: {
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
    },
    hybrid: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri'
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim() || !mapRef.current) return
    
    setIsSearching(true)
    try {
      // Using Nominatim (OpenStreetMap) geocoding API
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=1`
      )
      const data = await response.json()
      
      if (data && data.length > 0) {
        const { lat, lon } = data[0]
        const map = mapRef.current
        if (map) {
          map.setView([parseFloat(lat), parseFloat(lon)], 13)
        }
      }
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="relative w-full h-full" style={isSelectionMode ? { cursor: 'crosshair' } : undefined}>
      {/* Search bar */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-[1001] w-96">
        <div className="bg-gray-800 bg-opacity-95 rounded-lg shadow-lg p-2 flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder={t('map.search.placeholder')}
            className="flex-1 bg-gray-700 text-white px-3 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={disabled || isSearching}
          />
          <button
            onClick={handleSearch}
            disabled={disabled || isSearching}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <Search size={16} />
            {isSearching ? t('map.search.searching') : t('map.search.button')}
          </button>
        </div>
      </div>
      
      <MapContainer
        center={[37.7749, -122.4194]} // San Francisco
        zoom={13}
        style={{ height: '100%', width: '100%' }}
        ref={mapRef}
      >
        <TileLayer
          key={mapLayer}
          attribution={layerUrls[mapLayer].attribution}
          url={layerUrls[mapLayer].url}
          maxZoom={18}
        />
        {mapLayer === 'hybrid' && (
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap'
            opacity={0.3}
          />
        )}
        <BBoxSelector onBBoxSelected={onBBoxSelected} disabled={disabled} isSelectionMode={isSelectionMode} />
      </MapContainer>
      
      
      {/* Layer switcher and selection control */}
      <div className="absolute top-4 right-4 z-[999]">
        {/* Layer switcher */}
        <div className="bg-gray-800 bg-opacity-95 rounded-lg shadow-lg p-2 mb-2">
          <div className="flex items-center gap-2 mb-2 px-2">
            <Layers size={16} className="text-blue-400" />
            <span className="text-white text-sm font-semibold">{t('map.layers.title')}</span>
          </div>
          <div className="flex flex-col gap-1">
            <button
              onClick={() => setMapLayer('osm')}
              className={`px-3 py-2 rounded text-sm text-left transition-colors ${
                mapLayer === 'osm'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              {t('map.layers.street')}
            </button>
            <button
              onClick={() => setMapLayer('satellite')}
              className={`px-3 py-2 rounded text-sm text-left transition-colors ${
                mapLayer === 'satellite'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              {t('map.layers.satellite')}
            </button>
            <button
              onClick={() => setMapLayer('topo')}
              className={`px-3 py-2 rounded text-sm text-left transition-colors ${
                mapLayer === 'topo'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              {t('map.layers.topographic')}
            </button>
            <button
              onClick={() => setMapLayer('hybrid')}
              className={`px-3 py-2 rounded text-sm text-left transition-colors ${
                mapLayer === 'hybrid'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              {t('map.layers.hybrid')}
            </button>
          </div>
        </div>
        
        {/* Selection control */}
        <div className="bg-gray-800 bg-opacity-95 rounded-lg shadow-lg p-2">
          <button
            onClick={() => setIsSelectionMode(!isSelectionMode)}
            disabled={disabled}
            className={`w-full px-3 py-2 rounded text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
              isSelectionMode
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-md'
                : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
            } disabled:opacity-50`}
          >
            {isSelectionMode ? '✅' : '⬜'}
            <span className="text-xs">{isSelectionMode ? t('map.selectionMode.on') : t('map.selectionMode.off')}</span>
          </button>
        </div>
      </div>

      {/* Instructions overlay */}
      <div className="absolute bottom-4 left-4 bg-gray-800 bg-opacity-95 text-white px-4 py-3 rounded-lg shadow-xl z-[1000] max-w-xs backdrop-blur-sm border border-gray-700">
        <h3 className="font-semibold mb-2">{t('map.instructions.title')}</h3>
        <ol className="text-sm space-y-1 list-decimal list-inside">
          <li>{t('map.instructions.step1')}</li>
          <li>{t('map.instructions.step2')}</li>
          <li>{t('map.instructions.step3')}</li>
        </ol>
        <div className="mt-2 text-xs text-gray-300">
          {t('map.instructions.searchHint')}
        </div>
        {disabled && (
          <div className="mt-3 p-2 bg-yellow-900 bg-opacity-50 rounded text-yellow-200 text-xs">
            {t('map.instructions.disabled')}
          </div>
        )}
      </div>
    </div>
  )
}


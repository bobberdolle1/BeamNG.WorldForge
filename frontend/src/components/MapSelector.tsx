import type { Map as LeafletMap } from 'leaflet'
import { Layers, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MapContainer, Polyline, Rectangle, TileLayer, useMap, useMapEvents } from 'react-leaflet'

import { gridLines, measure, squareBoundsFrom, toLeafletBounds } from '../lib/selection'
import type { BoundingBox } from '../types'

import 'leaflet/dist/leaflet.css'

interface MapSelectorProps {
  onBBoxSelected: (bbox: BoundingBox) => void
  disabled?: boolean
}

function BBoxSelector({
  onBBoxSelected,
  disabled,
  isSelectionMode,
}: MapSelectorProps & { isSelectionMode: boolean }) {
  const [bbox, setBBox] = useState<BoundingBox | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const startRef = useRef<{ lat: number; lng: number } | null>(null)
  const map = useMap()

  // Leaflet pans the map on drag, which is the same gesture as drawing a box.
  // Suspending dragging while selection mode is on stops the map sliding out
  // from under the rectangle being drawn.
  useEffect(() => {
    if (isSelectionMode && !disabled) {
      map.dragging.disable()
    } else {
      map.dragging.enable()
    }
    return () => {
      map.dragging.enable()
    }
  }, [map, isSelectionMode, disabled])

  // A drag that ends outside the map never delivers Leaflet's mouseup, which
  // left the component stuck mid-selection with the rectangle following the
  // cursor forever. A window-level listener closes the gesture wherever it ends.
  useEffect(() => {
    if (!isCreating) {
      return
    }
    const finish = () => {
      setIsCreating(false)
      startRef.current = null
    }
    window.addEventListener('pointerup', finish)
    return () => window.removeEventListener('pointerup', finish)
  }, [isCreating])

  const update = (current: { lat: number; lng: number }, commit: boolean) => {
    const start = startRef.current
    if (!start) {
      return
    }

    const next = squareBoundsFrom(start, current)
    if (!next) {
      // Too small to be deliberate; keep whatever was already selected.
      return
    }

    setBBox(next)
    if (commit) {
      onBBoxSelected(next)
    }
  }

  useMapEvents({
    mousedown(event) {
      if (disabled || !isSelectionMode) return
      startRef.current = { lat: event.latlng.lat, lng: event.latlng.lng }
      setIsCreating(true)
      setBBox(null)
    },
    mousemove(event) {
      if (disabled || !isSelectionMode || !isCreating) return
      update({ lat: event.latlng.lat, lng: event.latlng.lng }, false)
    },
    mouseup(event) {
      if (disabled || !isSelectionMode || !isCreating) return
      update({ lat: event.latlng.lat, lng: event.latlng.lng }, true)
      setIsCreating(false)
      startRef.current = null
    },
  })

  if (!bbox) return null

  const { widthKm, heightKm, areaKm2, tooLarge } = measure(bbox)
  const stroke = tooLarge ? '#ef4444' : isCreating ? '#10b981' : '#3b82f6'

  return (
    <>
      <Rectangle
        bounds={toLeafletBounds(bbox)}
        pathOptions={{
          color: stroke,
          weight: 3,
          fillColor: stroke,
          fillOpacity: isCreating ? 0.15 : 0.2,
        }}
      />

      {gridLines(bbox).map((line) => (
        <Polyline
          key={line.map(([lat, lon]) => `${lat.toFixed(6)},${lon.toFixed(6)}`).join('|')}
          positions={line}
          pathOptions={{
            color: tooLarge ? '#fca5a5' : isCreating ? '#6ee7b7' : '#93c5fd',
            weight: 1.5,
            opacity: isCreating ? 0.5 : 0.7,
            dashArray: '3, 3',
          }}
        />
      ))}

      <div
        className="leaflet-top leaflet-right"
        style={{ marginTop: '80px', marginRight: '10px', zIndex: 1002 }}
      >
        <div
          className={`text-white px-3 py-2 rounded-lg shadow-xl text-xs font-semibold border-2 backdrop-blur-sm ${
            tooLarge
              ? 'bg-gradient-to-br from-red-600 to-red-700 border-red-400/50'
              : 'bg-gradient-to-br from-blue-600 to-blue-700 border-blue-400/50'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="text-base">{tooLarge ? '\u26a0\ufe0f' : '\ud83d\udccf'}</span>
            <div>
              <div className="font-bold">
                {widthKm.toFixed(2)} \u00d7 {heightKm.toFixed(2)} km
              </div>
              <div className="text-[10px] opacity-80">{areaKm2.toFixed(2)} km\u00b2</div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default function MapSelector({ onBBoxSelected, disabled }: MapSelectorProps) {
  const { t } = useTranslation()
  const mapRef = useRef<LeafletMap | null>(null)
  const [mapLayer, setMapLayer] = useState<'osm' | 'satellite' | 'topo' | 'hybrid'>('osm')
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [isSelectionMode, setIsSelectionMode] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

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
    const query = searchQuery.trim()
    if (!query || !mapRef.current) return

    setIsSearching(true)
    setSearchError(null)
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`,
        // Nominatim's usage policy requires an identifiable client.
        { headers: { Accept: 'application/json' } },
      )
      if (!response.ok) {
        throw new Error(`Search service returned ${response.status}`)
      }

      const results = await response.json()
      if (!Array.isArray(results) || results.length === 0) {
        setSearchError(`No place found for "${query}"`)
        return
      }

      mapRef.current.setView([parseFloat(results[0].lat), parseFloat(results[0].lon)], 13)
    } catch (error) {
      // Previously this only reached the console, so a failed search looked
      // identical to a search that simply did not move the map.
      setSearchError(error instanceof Error ? error.message : 'Search failed')
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
            onKeyDown={(event) => event.key === 'Enter' && handleSearch()}
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
        {searchError && (
          <div className="mt-1 bg-red-900/90 text-red-100 text-xs px-3 py-2 rounded" role="alert">
            {searchError}
          </div>
        )}
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


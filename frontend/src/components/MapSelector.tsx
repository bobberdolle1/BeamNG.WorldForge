import { useRef, useState } from 'react'
import { MapContainer, TileLayer, Rectangle, Polyline, useMapEvents } from 'react-leaflet'
import { LatLngBounds, LatLng } from 'leaflet'
import { BoundingBox } from '../types'
import { Layers } from 'lucide-react'
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

function BBoxSelector({ onBBoxSelected, disabled }: MapSelectorProps) {
  const [startPoint, setStartPoint] = useState<LatLng | null>(null)
  const [bounds, setBounds] = useState<LatLngBounds | null>(null)
  const [gridLines, setGridLines] = useState<Array<[number, number][]>>([])

  useMapEvents({
    mousedown(e) {
      if (disabled) return
      setStartPoint(e.latlng)
      setBounds(null)
      setGridLines([])
    },
    mousemove(e) {
      if (disabled || !startPoint) return
      
      // Calculate square bounds (equal width and height in degrees)
      const latDiff = Math.abs(e.latlng.lat - startPoint.lat)
      const lonDiff = Math.abs(e.latlng.lng - startPoint.lng)
      const maxDiff = Math.max(latDiff, lonDiff)
      
      const squareBounds = new LatLngBounds(
        [startPoint.lat, startPoint.lng],
        [
          startPoint.lat + (e.latlng.lat > startPoint.lat ? maxDiff : -maxDiff),
          startPoint.lng + (e.latlng.lng > startPoint.lng ? maxDiff : -maxDiff)
        ]
      )
      
      setBounds(squareBounds)
      
      // Generate grid lines (4x4 grid)
      const south = squareBounds.getSouth()
      const north = squareBounds.getNorth()
      const west = squareBounds.getWest()
      const east = squareBounds.getEast()
      
      const latStep = (north - south) / 4
      const lonStep = (east - west) / 4
      
      const lines: Array<[number, number][]> = []
      
      // Horizontal lines
      for (let i = 1; i < 4; i++) {
        const lat = south + latStep * i
        lines.push([[lat, west], [lat, east]])
      }
      
      // Vertical lines
      for (let i = 1; i < 4; i++) {
        const lon = west + lonStep * i
        lines.push([[south, lon], [north, lon]])
      }
      
      setGridLines(lines)
    },
    mouseup(e) {
      if (disabled || !startPoint) return
      
      // Calculate square bounds
      const latDiff = Math.abs(e.latlng.lat - startPoint.lat)
      const lonDiff = Math.abs(e.latlng.lng - startPoint.lng)
      const maxDiff = Math.max(latDiff, lonDiff)
      
      const finalBounds = new LatLngBounds(
        [startPoint.lat, startPoint.lng],
        [
          startPoint.lat + (e.latlng.lat > startPoint.lat ? maxDiff : -maxDiff),
          startPoint.lng + (e.latlng.lng > startPoint.lng ? maxDiff : -maxDiff)
        ]
      )
      
      setBounds(finalBounds)
      
      // Convert to BoundingBox
      const bbox: BoundingBox = {
        min_lat: finalBounds.getSouth(),
        max_lat: finalBounds.getNorth(),
        min_lon: finalBounds.getWest(),
        max_lon: finalBounds.getEast(),
      }
      
      onBBoxSelected(bbox)
      
      // Reset for next selection
      setStartPoint(null)
    },
  })

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
          color: '#3b82f6',
          weight: 3,
          fillColor: '#3b82f6',
          fillOpacity: 0.15,
        }}
      />
      
      {/* Grid lines */}
      {gridLines.map((line, idx) => (
        <Polyline
          key={idx}
          positions={line as any}
          pathOptions={{
            color: '#60a5fa',
            weight: 1,
            opacity: 0.5,
            dashArray: '5, 5'
          }}
        />
      ))}
      
      {/* Size label overlay - rendered outside map */}
      {typeof window !== 'undefined' && (
        <div
          className="absolute bg-blue-600 text-white px-3 py-2 rounded-lg shadow-lg text-sm font-semibold z-[1000] pointer-events-none"
          style={{
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)'
          }}
        >
          📏 {width.toFixed(2)} × {height.toFixed(2)} km
          <div className="text-xs opacity-90 mt-1">
            {(width / height).toFixed(2)}:1 ratio
          </div>
        </div>
      )}
    </>
  )
}

export default function MapSelector({ onBBoxSelected, disabled }: MapSelectorProps) {
  const mapRef = useRef<any>(null)
  const [mapLayer, setMapLayer] = useState<'osm' | 'satellite' | 'topo' | 'hybrid'>('osm')

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

  return (
    <div className="relative w-full h-full">
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
        <BBoxSelector onBBoxSelected={onBBoxSelected} disabled={disabled} />
      </MapContainer>
      
      {/* Layer switcher */}
      <div className="absolute top-4 right-4 bg-gray-800 bg-opacity-95 rounded-lg shadow-lg z-[1000] p-2">
        <div className="flex items-center gap-2 mb-2 px-2">
          <Layers size={16} className="text-blue-400" />
          <span className="text-white text-sm font-semibold">Map Layer</span>
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
            🗺️ Street Map
          </button>
          <button
            onClick={() => setMapLayer('satellite')}
            className={`px-3 py-2 rounded text-sm text-left transition-colors ${
              mapLayer === 'satellite'
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            }`}
          >
            🛰️ Satellite
          </button>
          <button
            onClick={() => setMapLayer('topo')}
            className={`px-3 py-2 rounded text-sm text-left transition-colors ${
              mapLayer === 'topo'
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            }`}
          >
            ⛰️ Topographic
          </button>
          <button
            onClick={() => setMapLayer('hybrid')}
            className={`px-3 py-2 rounded text-sm text-left transition-colors ${
              mapLayer === 'hybrid'
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            }`}
          >
            🌍 Hybrid
          </button>
        </div>
      </div>

      {/* Instructions overlay */}
      <div className="absolute top-4 left-4 bg-gray-800 bg-opacity-90 text-white px-4 py-3 rounded-lg shadow-lg z-[1000] max-w-xs">
        <h3 className="font-semibold mb-2">How to use:</h3>
        <ol className="text-sm space-y-1 list-decimal list-inside">
          <li>Click and drag on the map to select a region</li>
          <li>Configure settings in the right panel</li>
          <li>Click "Generate Map" to start</li>
        </ol>
        {disabled && (
          <div className="mt-3 p-2 bg-yellow-900 bg-opacity-50 rounded text-yellow-200 text-xs">
            Map selection disabled during generation
          </div>
        )}
      </div>
    </div>
  )
}


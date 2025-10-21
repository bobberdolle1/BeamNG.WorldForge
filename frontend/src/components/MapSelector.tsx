import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, Rectangle, useMapEvents } from 'react-leaflet'
import { LatLngBounds, LatLng } from 'leaflet'
import { BoundingBox } from '../types'
import 'leaflet/dist/leaflet.css'

interface MapSelectorProps {
  onBBoxSelected: (bbox: BoundingBox) => void
  disabled?: boolean
}

function BBoxSelector({ onBBoxSelected, disabled }: MapSelectorProps) {
  const [startPoint, setStartPoint] = useState<LatLng | null>(null)
  const [endPoint, setEndPoint] = useState<LatLng | null>(null)
  const [bounds, setBounds] = useState<LatLngBounds | null>(null)

  useMapEvents({
    mousedown(e) {
      if (disabled) return
      setStartPoint(e.latlng)
      setEndPoint(null)
      setBounds(null)
    },
    mousemove(e) {
      if (disabled || !startPoint) return
      setEndPoint(e.latlng)
      
      const newBounds = new LatLngBounds(startPoint, e.latlng)
      setBounds(newBounds)
    },
    mouseup(e) {
      if (disabled || !startPoint) return
      
      const finalBounds = new LatLngBounds(startPoint, e.latlng)
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
      setEndPoint(null)
    },
  })

  return bounds ? (
    <Rectangle
      bounds={bounds}
      pathOptions={{
        color: '#0ea5e9',
        weight: 2,
        fillColor: '#0ea5e9',
        fillOpacity: 0.2,
      }}
    />
  ) : null
}

export default function MapSelector({ onBBoxSelected, disabled }: MapSelectorProps) {
  const mapRef = useRef<any>(null)

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={[37.7749, -122.4194]} // San Francisco
        zoom={13}
        style={{ height: '100%', width: '100%' }}
        ref={mapRef}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <BBoxSelector onBBoxSelected={onBBoxSelected} disabled={disabled} />
      </MapContainer>

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


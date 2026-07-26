import { X } from 'lucide-react'
import { Suspense, lazy } from 'react'

import type { BuildingFeature, MapBounds, RoadFeature } from '../types'

/*
 * Three.js and @react-three/* account for roughly two thirds of the bundle,
 * and the 3D preview is opened only after a map has finished generating - so
 * eagerly bundling it made every first page load pay for a feature most
 * sessions never reach. Loading it on demand cuts the initial download
 * substantially and costs a brief spinner the first time the modal is opened.
 */
const ThreePreview = lazy(() => import('./ThreePreview'))

interface PreviewPanelProps {
  isOpen: boolean
  onClose: () => void
  mapData: {
    heightmapUrl: string
    roads?: RoadFeature[]
    buildings?: BuildingFeature[]
    mapBounds?: MapBounds
    mapSize: number
  }
}


export const PreviewPanel = ({ isOpen, onClose, mapData }: PreviewPanelProps) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">🎮 3D Preview</h2>
            <p className="text-sm text-gray-400 mt-1">
              Use mouse to rotate • Scroll to zoom • Right-click to pan
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>
        
        {/* 3D Preview */}
        <div className="flex-1 bg-gray-900 rounded-lg overflow-hidden" style={{ minHeight: '500px' }}>
          {mapData.heightmapUrl ? (
            <Suspense
              fallback={
                <div className="flex items-center justify-center h-full text-gray-400">
                  Loading 3D viewer...
                </div>
              }
            >
              <ThreePreview
                heightmapUrl={mapData.heightmapUrl}
                mapSize={String(mapData.mapSize)}
              />
            </Suspense>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <div className="text-4xl mb-3">🎮</div>
                <p>No heightmap data available</p>
              </div>
            </div>
          )}
        </div>

        {/* Info panel */}
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div className="bg-gray-700 rounded p-3">
            <div className="text-gray-400 mb-1">Map Size</div>
            <div className="text-white font-semibold">{mapData.mapSize} km²</div>
          </div>
          {mapData.mapBounds && (
            <div className="bg-gray-700 rounded p-3">
              <div className="text-gray-400 mb-1">Coordinates</div>
              <div className="text-white font-mono text-xs">
                {mapData.mapBounds.minLat.toFixed(4)}, {mapData.mapBounds.minLon.toFixed(4)}
              </div>
            </div>
          )}
          {mapData.roads && mapData.roads.length > 0 && (
            <div className="bg-gray-700 rounded p-3">
              <div className="text-gray-400 mb-1">Roads</div>
              <div className="text-white font-semibold">{mapData.roads.length} detected</div>
            </div>
          )}
        </div>

        {/* Tips */}
        <div className="mt-4 bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-3">
          <p className="text-xs text-blue-200">
            <strong>💡 Tip:</strong> This is a preview visualization. The actual BeamNG.drive map will have higher quality textures and physics.
          </p>
        </div>
      </div>
    </div>
  )
}

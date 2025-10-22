import { useRef, useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'

interface PreviewPanelProps {
  isOpen: boolean
  onClose: () => void
  mapData: {
    heightmapUrl: string
    roads?: any[]
    buildings?: any[]
    mapBounds?: {
      minLat: number
      maxLat: number
      minLon: number
      maxLon: number
    }
    mapSize: number
  }
}

function TerrainMesh({ heightmapUrl }: { heightmapUrl: string }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [geometry, setGeometry] = useState<THREE.PlaneGeometry | null>(null)

  useEffect(() => {
    if (!heightmapUrl) return

    const loader = new THREE.TextureLoader()
    loader.load(
      heightmapUrl,
      (texture) => {
        const canvas = document.createElement('canvas')
        const context = canvas.getContext('2d')
        if (!context) return

        const img = texture.image
        canvas.width = img.width
        canvas.height = img.height
        context.drawImage(img, 0, 0)

        const imageData = context.getImageData(0, 0, canvas.width, canvas.height)
        const data = imageData.data

        // Create plane geometry
        const width = 100
        const height = 100
        const widthSegments = Math.min(canvas.width, 256)
        const heightSegments = Math.min(canvas.height, 256)

        const planeGeometry = new THREE.PlaneGeometry(
          width,
          height,
          widthSegments - 1,
          heightSegments - 1
        )

        // Apply heightmap data to vertices
        const vertices = planeGeometry.attributes.position
        for (let i = 0; i < vertices.count; i++) {
          const x = Math.floor((i % widthSegments) * (canvas.width / widthSegments))
          const y = Math.floor(Math.floor(i / widthSegments) * (canvas.height / heightSegments))
          const index = (y * canvas.width + x) * 4
          const height = (data[index] / 255) * 20 // Scale height
          vertices.setZ(i, height)
        }

        planeGeometry.computeVertexNormals()
        setGeometry(planeGeometry)
      },
      undefined,
      (error) => {
        console.error('Error loading heightmap:', error)
      }
    )
  }, [heightmapUrl])

  if (!geometry) {
    return (
      <mesh>
        <planeGeometry args={[100, 100, 50, 50]} />
        <meshStandardMaterial color="#4a5568" wireframe />
      </mesh>
    )
  }

  return (
    <mesh ref={meshRef} geometry={geometry} rotation={[-Math.PI / 2, 0, 0]}>
      <meshStandardMaterial 
        color="#8b7355"
        wireframe={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

function Scene({ mapData }: { mapData: PreviewPanelProps['mapData'] }) {
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
      <directionalLight position={[-10, 10, -5]} intensity={0.5} />

      {/* Terrain */}
      {mapData.heightmapUrl && <TerrainMesh heightmapUrl={mapData.heightmapUrl} />}

      {/* Grid helper */}
      <gridHelper args={[200, 20, '#444444', '#222222']} position={[0, 0, 0]} />
      
      {/* Axis helper */}
      <axesHelper args={[50]} />

      {/* Camera and controls */}
      <PerspectiveCamera makeDefault position={[50, 40, 50]} fov={60} />
      <OrbitControls 
        enableDamping 
        dampingFactor={0.05}
        minDistance={20}
        maxDistance={200}
        maxPolarAngle={Math.PI / 2 - 0.1}
      />
    </>
  )
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
        
        {/* 3D Canvas */}
        <div className="flex-1 bg-gray-900 rounded-lg overflow-hidden" style={{ minHeight: '500px' }}>
          <Canvas shadows>
            <Scene mapData={mapData} />
          </Canvas>
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

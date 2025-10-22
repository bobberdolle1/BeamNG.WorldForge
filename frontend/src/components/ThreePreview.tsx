import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface ThreePreviewProps {
  heightmapUrl: string
  mapSize?: string
}

export default function ThreePreview({ heightmapUrl, mapSize }: ThreePreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const meshRef = useRef<THREE.Mesh | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a1a2e)
    scene.fog = new THREE.Fog(0x1a1a2e, 50, 200)
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
    camera.position.set(50, 40, 50)
    camera.lookAt(0, 0, 0)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1)
    directionalLight.position.set(50, 50, 25)
    directionalLight.castShadow = true
    directionalLight.shadow.mapSize.width = 2048
    directionalLight.shadow.mapSize.height = 2048
    scene.add(directionalLight)

    const directionalLight2 = new THREE.DirectionalLight(0x6495ed, 0.3)
    directionalLight2.position.set(-50, 30, -25)
    scene.add(directionalLight2)

    // Grid
    const gridHelper = new THREE.GridHelper(200, 40, 0x444444, 0x222222)
    scene.add(gridHelper)

    // Axes
    const axesHelper = new THREE.AxesHelper(50)
    scene.add(axesHelper)

    // Load heightmap and create terrain
    const textureLoader = new THREE.TextureLoader()
    textureLoader.load(
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

        const terrainWidth = 100
        const terrainHeight = 100
        const segmentsW = Math.min(canvas.width, 256)
        const segmentsH = Math.min(canvas.height, 256)

        const geometry = new THREE.PlaneGeometry(
          terrainWidth,
          terrainHeight,
          segmentsW - 1,
          segmentsH - 1
        )

        const vertices = geometry.attributes.position
        for (let i = 0; i < vertices.count; i++) {
          const x = Math.floor((i % segmentsW) * (canvas.width / segmentsW))
          const y = Math.floor(Math.floor(i / segmentsW) * (canvas.height / segmentsH))
          const index = (y * canvas.width + x) * 4
          const heightValue = (data[index] / 255) * 20
          vertices.setZ(i, heightValue)
        }

        geometry.computeVertexNormals()

        const material = new THREE.MeshStandardMaterial({
          color: 0x8b7355,
          roughness: 0.8,
          metalness: 0.2,
          flatShading: false,
        })

        const mesh = new THREE.Mesh(geometry, material)
        mesh.rotation.x = -Math.PI / 2
        mesh.receiveShadow = true
        mesh.castShadow = true
        scene.add(mesh)
        meshRef.current = mesh
      },
      undefined,
      (error) => {
        console.error('Error loading heightmap:', error)
        
        // Fallback: create flat plane
        const geometry = new THREE.PlaneGeometry(100, 100, 50, 50)
        const material = new THREE.MeshStandardMaterial({
          color: 0x4a5568,
          wireframe: true,
        })
        const mesh = new THREE.Mesh(geometry, material)
        mesh.rotation.x = -Math.PI / 2
        scene.add(mesh)
        meshRef.current = mesh
      }
    )

    // Mouse controls (orbit)
    let isDragging = false
    let previousMousePosition = { x: 0, y: 0 }
    let cameraAngle = { theta: Math.PI / 4, phi: Math.PI / 6 }
    let cameraDistance = 80

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true
      previousMousePosition = { x: e.clientX, y: e.clientY }
    }

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return

      const deltaX = e.clientX - previousMousePosition.x
      const deltaY = e.clientY - previousMousePosition.y

      cameraAngle.theta -= deltaX * 0.01
      cameraAngle.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.1, cameraAngle.phi - deltaY * 0.01))

      previousMousePosition = { x: e.clientX, y: e.clientY }
    }

    const onMouseUp = () => {
      isDragging = false
    }

    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      cameraDistance = Math.max(20, Math.min(200, cameraDistance + e.deltaY * 0.1))
    }

    container.addEventListener('mousedown', onMouseDown)
    container.addEventListener('mousemove', onMouseMove)
    container.addEventListener('mouseup', onMouseUp)
    container.addEventListener('wheel', onWheel, { passive: false })

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate)

      // Update camera position
      camera.position.x = cameraDistance * Math.sin(cameraAngle.theta) * Math.cos(cameraAngle.phi)
      camera.position.y = cameraDistance * Math.sin(cameraAngle.phi)
      camera.position.z = cameraDistance * Math.cos(cameraAngle.theta) * Math.cos(cameraAngle.phi)
      camera.lookAt(0, 0, 0)

      // Rotate mesh slowly
      if (meshRef.current) {
        meshRef.current.rotation.z += 0.0005
      }

      renderer.render(scene, camera)
    }
    animate()

    // Handle window resize
    const handleResize = () => {
      if (!containerRef.current) return
      const newWidth = containerRef.current.clientWidth
      const newHeight = containerRef.current.clientHeight

      camera.aspect = newWidth / newHeight
      camera.updateProjectionMatrix()
      renderer.setSize(newWidth, newHeight)
    }
    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      container.removeEventListener('mousedown', onMouseDown)
      container.removeEventListener('mousemove', onMouseMove)
      container.removeEventListener('mouseup', onMouseUp)
      container.removeEventListener('wheel', onWheel)
      window.removeEventListener('resize', handleResize)
      
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
      renderer.dispose()
      
      if (meshRef.current) {
        meshRef.current.geometry.dispose()
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach(m => m.dispose())
        } else {
          meshRef.current.material.dispose()
        }
      }
    }
  }, [heightmapUrl])

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      
      {/* Controls hint */}
      <div className="absolute bottom-4 left-4 bg-gray-800 bg-opacity-90 text-white px-3 py-2 rounded text-xs">
        🖱️ Drag to rotate • Scroll to zoom
      </div>
      
      {/* Info badge */}
      <div className="absolute top-4 right-4 bg-blue-600 text-white px-3 py-2 rounded-lg text-xs font-semibold">
        ✨ 3D Preview {mapSize && `• ${mapSize}`}
      </div>
    </div>
  )
}

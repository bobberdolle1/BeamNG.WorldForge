import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Grid } from '@react-three/drei';
import { Suspense } from 'react';

interface Scene3DProps {
  children?: React.ReactNode;
}

export const Scene3D: React.FC<Scene3DProps> = ({ children }) => {
  return (
    <div className="w-full h-full relative">
      <Canvas shadows>
        <Suspense fallback={null}>
          {/* Camera */}
          <PerspectiveCamera makeDefault position={[0, 50, 100]} fov={60} />
          
          {/* Controls */}
          <OrbitControls
            enableDamping
            dampingFactor={0.05}
            minDistance={10}
            maxDistance={500}
            maxPolarAngle={Math.PI / 2}
          />
          
          {/* Lighting */}
          <ambientLight intensity={0.5} />
          <directionalLight
            position={[50, 100, 50]}
            intensity={1}
            castShadow
            shadow-mapSize-width={2048}
            shadow-mapSize-height={2048}
            shadow-camera-far={200}
            shadow-camera-left={-100}
            shadow-camera-right={100}
            shadow-camera-top={100}
            shadow-camera-bottom={-100}
          />
          
          {/* Ground Grid */}
          <Grid
            args={[200, 200]}
            cellSize={10}
            cellThickness={0.5}
            cellColor="#6b7280"
            sectionSize={50}
            sectionThickness={1}
            sectionColor="#9ca3af"
            fadeDistance={400}
            fadeStrength={1}
            infiniteGrid
          />
          
          {/* Children (Terrain, Roads, Buildings, etc.) */}
          {children}
        </Suspense>
      </Canvas>
      
      {/* FPS Counter */}
      <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-2 rounded text-sm font-mono">
        <div>FPS: <span id="fps">60</span></div>
        <div>Objects: <span id="objects">0</span></div>
      </div>
      
      {/* Controls Help */}
      <div className="absolute bottom-4 left-4 bg-black/70 text-white px-3 py-2 rounded text-sm">
        <div className="font-semibold mb-1">🎮 Controls:</div>
        <div>Left Mouse: Rotate</div>
        <div>Right Mouse: Pan</div>
        <div>Scroll: Zoom</div>
      </div>
    </div>
  );
};


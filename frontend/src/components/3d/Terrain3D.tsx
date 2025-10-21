import { useLoader } from '@react-three/fiber';
import { TextureLoader } from 'three';
import * as THREE from 'three';
import { useMemo } from 'react';

interface Terrain3DProps {
  heightmapUrl: string;
  size?: number;
  heightScale?: number;
  resolution?: number;
}

export const Terrain3D: React.FC<Terrain3DProps> = ({
  heightmapUrl,
  size = 100,
  heightScale = 20,
  resolution = 128,
}) => {
  // Load heightmap texture
  const displacementMap = useLoader(TextureLoader, heightmapUrl);
  
  // Create geometry with high resolution
  const geometry = useMemo(() => {
    return new THREE.PlaneGeometry(
      size,
      size,
      resolution - 1,
      resolution - 1
    );
  }, [size, resolution]);
  
  return (
    <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]} receiveShadow castShadow>
      <meshStandardMaterial
        color="#8b7355"
        displacementMap={displacementMap}
        displacementScale={heightScale}
        roughness={0.9}
        metalness={0}
      />
    </mesh>
  );
};


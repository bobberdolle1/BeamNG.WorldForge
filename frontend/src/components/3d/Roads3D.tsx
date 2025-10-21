import { useMemo } from 'react';
import * as THREE from 'three';

interface Road {
  centerline: [number, number][];
  width: number;
  type: string;
}

interface Roads3DProps {
  roads: Road[];
  mapBounds: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  };
  mapSize: number;
}

export const Roads3D: React.FC<Roads3DProps> = ({ roads, mapBounds, mapSize }) => {
  const roadMeshes = useMemo(() => {
    if (!roads || roads.length === 0) return [];
    
    return roads.map((road, index) => {
      // Convert lat/lon to local coordinates
      const points = road.centerline.map(([lat, lon]) => {
        const x = ((lon - mapBounds.minLon) / (mapBounds.maxLon - mapBounds.minLon) - 0.5) * mapSize;
        const z = ((lat - mapBounds.minLat) / (mapBounds.maxLat - mapBounds.minLat) - 0.5) * mapSize;
        return new THREE.Vector3(x, 1, z); // y=1 to place slightly above terrain
      });
      
      if (points.length < 2) return null;
      
      // Create curve from points
      const curve = new THREE.CatmullRomCurve3(points);
      
      // Create tube geometry for 3D road
      const tubeGeometry = new THREE.TubeGeometry(
        curve,
        Math.min(points.length * 10, 200), // segments
        road.width / 2 || 2, // radius
        8, // radial segments
        false // closed
      );
      
      return { geometry: tubeGeometry, key: `road-${index}` };
    }).filter(Boolean);
  }, [roads, mapBounds, mapSize]);
  
  return (
    <group>
      {roadMeshes.map((road) => road && (
        <mesh key={road.key} geometry={road.geometry} castShadow>
          <meshStandardMaterial
            color="#2c2c2c"
            roughness={0.7}
            metalness={0.1}
          />
        </mesh>
      ))}
    </group>
  );
};


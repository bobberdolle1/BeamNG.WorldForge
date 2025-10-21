import { useMemo } from 'react';
import * as THREE from 'three';

interface Building {
  footprint: [number, number][];
  height: number;
  type: string;
}

interface Buildings3DProps {
  buildings: Building[];
  mapBounds: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  };
  mapSize: number;
}

export const Buildings3D: React.FC<Buildings3DProps> = ({ buildings, mapBounds, mapSize }) => {
  const buildingMeshes = useMemo(() => {
    if (!buildings || buildings.length === 0) return [];
    
    return buildings.map((building, index) => {
      // Convert footprint to local coordinates
      const shape = new THREE.Shape();
      
      building.footprint.forEach(([lat, lon], i) => {
        const x = ((lon - mapBounds.minLon) / (mapBounds.maxLon - mapBounds.minLon) - 0.5) * mapSize;
        const z = ((lat - mapBounds.minLat) / (mapBounds.maxLat - mapBounds.minLat) - 0.5) * mapSize;
        
        if (i === 0) {
          shape.moveTo(x, z);
        } else {
          shape.lineTo(x, z);
        }
      });
      
      // Close the shape
      shape.closePath();
      
      // Extrude geometry for 3D building
      const extrudeSettings = {
        depth: building.height || 10,
        bevelEnabled: false,
      };
      
      const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      
      // Rotate to stand upright
      geometry.rotateX(Math.PI / 2);
      
      return { geometry, key: `building-${index}`, type: building.type };
    });
  }, [buildings, mapBounds, mapSize]);
  
  // Different colors for different building types
  const getBuildingColor = (type: string) => {
    switch (type) {
      case 'residential':
        return '#c7dff8';
      case 'commercial':
        return '#94a3b8';
      case 'industrial':
        return '#78716c';
      default:
        return '#a8a29e';
    }
  };
  
  return (
    <group>
      {buildingMeshes.map((building) => (
        <mesh key={building.key} geometry={building.geometry} castShadow receiveShadow>
          <meshStandardMaterial
            color={getBuildingColor(building.type)}
            roughness={0.8}
            metalness={0.2}
          />
        </mesh>
      ))}
    </group>
  );
};


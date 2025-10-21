import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface Vehicle {
  mesh: THREE.Mesh;
  position: THREE.Vector3;
  roadIndex: number;
  progress: number;
  speed: number;
}

interface TrafficSimProps {
  roads: any[];
  mapBounds: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  };
  mapSize: number;
  vehicleCount?: number;
  enabled?: boolean;
}

export const TrafficSim: React.FC<TrafficSimProps> = ({
  roads,
  mapBounds,
  mapSize,
  vehicleCount = 5,
  enabled = true,
}) => {
  const groupRef = useRef<THREE.Group>(null);
  
  // Create road curves for path following
  const roadCurves = useMemo(() => {
    if (!roads || roads.length === 0) return [];
    
    return roads.map(road => {
      const points = road.centerline.map(([lat, lon]: [number, number]) => {
        const x = ((lon - mapBounds.minLon) / (mapBounds.maxLon - mapBounds.minLon) - 0.5) * mapSize;
        const z = ((lat - mapBounds.minLat) / (mapBounds.maxLat - mapBounds.minLat) - 0.5) * mapSize;
        return new THREE.Vector3(x, 2, z); // y=2 to place above terrain
      });
      
      if (points.length < 2) return null;
      return new THREE.CatmullRomCurve3(points);
    }).filter(Boolean);
  }, [roads, mapBounds, mapSize]);
  
  // Create vehicles
  const vehicles = useMemo(() => {
    if (roadCurves.length === 0) return [];
    
    const cars: Vehicle[] = [];
    
    for (let i = 0; i < Math.min(vehicleCount, roadCurves.length * 3); i++) {
      // Simple car geometry (box)
      const geometry = new THREE.BoxGeometry(2, 1, 4);
      const material = new THREE.MeshStandardMaterial({
        color: ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'][i % 5],
        metalness: 0.8,
        roughness: 0.2,
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      
      cars.push({
        mesh,
        position: new THREE.Vector3(),
        roadIndex: Math.floor(Math.random() * roadCurves.length),
        progress: Math.random(), // Random starting position
        speed: 0.01 + Math.random() * 0.02, // Random speed
      });
    }
    
    return cars;
  }, [roadCurves, vehicleCount]);
  
  // Animation loop
  useFrame((_state, delta) => {
    if (!enabled || roadCurves.length === 0 || !groupRef.current) return;
    
    vehicles.forEach(vehicle => {
      // Update progress along road
      vehicle.progress += vehicle.speed * delta;
      
      // Loop back to start
      if (vehicle.progress >= 1.0) {
        vehicle.progress = 0;
        // Optionally switch to another road
        if (Math.random() > 0.7) {
          vehicle.roadIndex = Math.floor(Math.random() * roadCurves.length);
        }
      }
      
      const curve = roadCurves[vehicle.roadIndex];
      if (!curve) return;
      
      // Get position on curve
      const point = curve.getPointAt(vehicle.progress);
      vehicle.mesh.position.copy(point);
      
      // Get direction for rotation
      const tangent = curve.getTangentAt(vehicle.progress);
      const angle = Math.atan2(tangent.x, tangent.z);
      vehicle.mesh.rotation.y = angle;
    });
  });
  
  return (
    <group ref={groupRef}>
      {vehicles.map((vehicle, i) => (
        <primitive key={`vehicle-${i}`} object={vehicle.mesh} />
      ))}
    </group>
  );
};


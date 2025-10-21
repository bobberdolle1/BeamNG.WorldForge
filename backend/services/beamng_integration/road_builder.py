"""Build road network in BeamNG.drive format"""

import json
from typing import List, Dict, Any
from pathlib import Path


class RoadBuilder:
    """
    Convert JBeam roads to BeamNG decalRoad format
    """
    
    def __init__(self):
        print(f"🛣️  Road Builder initialized")
    
    def create_decal_roads(
        self,
        roads_vector_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create decalRoad.json from vector road data
        
        Args:
            roads_vector_data: Road vectors from Этап 2
                [{"centerline": [[lat, lon], ...], "width": 10.0, "type": "highway"}, ...]
        
        Returns:
            decalRoad.json structure
        """
        print(f"🛣️  Creating decal roads for {len(roads_vector_data)} roads...")
        
        roads = []
        
        for idx, road in enumerate(roads_vector_data, 1):
            decal_road = self._create_single_decal_road(road, idx)
            roads.append(decal_road)
        
        decal_road_json = {
            "version": 1,
            "roads": roads
        }
        
        print(f"✅ Decal roads created: {len(roads)}")
        return decal_road_json
    
    def _create_single_decal_road(
        self,
        road_data: Dict[str, Any],
        road_id: int
    ) -> Dict[str, Any]:
        """
        Create single decal road entry
        
        Args:
            road_data: Road vector data
            road_id: Road ID
        
        Returns:
            Decal road dict
        """
        centerline = road_data.get("centerline", [])
        width = road_data.get("width", 8.0)
        road_type = road_data.get("type", "residential")
        
        # Convert to BeamNG nodes format
        nodes = []
        for lat, lon in centerline:
            # Convert lat/lon to BeamNG coordinates
            x = lon * 111000  # Simplified conversion
            y = lat * 111000
            z = 0.0  # Would use heightmap in real implementation
            
            node = {
                "pos": [x, y, z],
                "width": width,
                "offset": 0.0
            }
            nodes.append(node)
        
        # Material based on type
        material_map = {
            "highway": "road_asphalt_highway",
            "primary": "road_asphalt",
            "secondary": "road_asphalt",
            "residential": "road_asphalt_residential",
            "dirt": "road_dirt",
            "gravel": "road_gravel"
        }
        material = material_map.get(road_type.lower(), "road_asphalt")
        
        decal_road = {
            "name": f"road_{road_id:03d}",
            "class": "DecalRoad",
            "drivability": 1.0 if road_type != "dirt" else 0.7,
            "lanes": [
                {
                    "width": width,
                    "material": material
                }
            ],
            "nodes": nodes,
            "renderPriority": 10,
            "breakAngle": 3.0,
            "textureLength": 5.0,
            "lanesLeft": 1,
            "lanesRight": 1
        }
        
        return decal_road
    
    def save_decal_roads(self, decal_roads: Dict[str, Any], output_path: Path):
        """
        Save decalRoad.json
        
        Args:
            decal_roads: Decal roads structure
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(decal_roads, f, indent=2)
        
        print(f"💾 Decal roads saved: {output_path}")


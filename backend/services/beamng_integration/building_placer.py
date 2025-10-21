"""Place buildings in BeamNG.drive level"""

import json
from typing import List, Dict, Any
from pathlib import Path


class BuildingPlacer:
    """
    Place building meshes in BeamNG.drive level
    """
    
    def __init__(self):
        print(f"🏢 Building Placer initialized")
    
    def create_building_items(
        self,
        buildings_vector_data: List[Dict[str, Any]],
        mesh_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create items.level.json entries for buildings
        
        Args:
            buildings_vector_data: Building vectors from Этап 2
            mesh_files: List of mesh file paths (.dae)
        
        Returns:
            List of building items for items.level.json
        """
        print(f"🏢 Creating building items for {len(buildings_vector_data)} buildings...")
        
        items = []
        
        for idx, (building, mesh_file) in enumerate(zip(buildings_vector_data, mesh_files), 1):
            item = self._create_single_building_item(building, mesh_file, idx)
            items.append(item)
        
        print(f"✅ Building items created: {len(items)}")
        return items
    
    def _create_single_building_item(
        self,
        building_data: Dict[str, Any],
        mesh_file: str,
        building_id: int
    ) -> Dict[str, Any]:
        """
        Create single building item entry
        
        Args:
            building_data: Building vector data
            mesh_file: Mesh file path
            building_id: Building ID
        
        Returns:
            Building item dict
        """
        footprint = building_data.get("footprint", [])
        height = building_data.get("height", 10.0)
        building_type = building_data.get("type", "residential")
        
        # Calculate center position from footprint
        if footprint:
            center_lat = sum(p[0] for p in footprint) / len(footprint)
            center_lon = sum(p[1] for p in footprint) / len(footprint)
            
            # Convert to BeamNG coordinates
            x = center_lon * 111000
            y = center_lat * 111000
            z = 0.0  # Ground level
        else:
            x, y, z = 0.0, 0.0, 0.0
        
        # Building item for BeamNG
        item = {
            "class": "TSStatic",
            "persistentId": f"building_{building_id}",
            "name": f"Building_{building_id:03d}",
            "position": [x, y, z],
            "rotation": [0, 0, 0, 1],  # Quaternion (no rotation)
            "scale": [1.0, 1.0, 1.0],
            "shapeName": mesh_file,
            "collisionType": "Visible Mesh",
            "decalType": "None",
            "renderBin": "Interior",
            "useInstanceRenderData": False,
            "meshCulling": True,
            "originSort": False,
            "forceDetail": -1,
            "__type": "TSStatic"
        }
        
        return item
    
    def update_items_level(
        self,
        existing_items: List[Dict[str, Any]],
        new_buildings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge new buildings into existing items
        
        Args:
            existing_items: Existing items from level
            new_buildings: New building items
        
        Returns:
            Merged items list
        """
        # Simply append new buildings
        merged = existing_items + new_buildings
        
        print(f"✅ Items merged: {len(existing_items)} existing + {len(new_buildings)} new = {len(merged)} total")
        return merged
    
    def save_items_level(self, items: List[Dict[str, Any]], output_path: Path):
        """
        Save items.level.json
        
        Args:
            items: Items list
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        items_json = {
            "version": 1,
            "items": items
        }
        
        with open(output_path, 'w') as f:
            json.dump(items_json, f, indent=2)
        
        print(f"💾 Items level saved: {output_path}")


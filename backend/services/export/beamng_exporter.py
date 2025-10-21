"""Export generated maps to BeamNG.drive mod format"""

import json
import zipfile
from pathlib import Path
from typing import Optional
import shutil


class BeamNGExporter:
    """
    Export map data to BeamNG.drive compatible mod structure
    
    BeamNG.drive mod structure:
    modname.zip/
    ├── levels/
    │   └── modname/
    │       ├── info.json           # Map metadata
    │       ├── main.level.json     # Level configuration
    │       ├── art/
    │       │   └── terrains/
    │       │       └── terrain_name/
    │       │           ├── heightmap.png  # 16-bit heightmap
    │       │           └── layers.json    # Terrain layers
    │       └── items.level.json    # Objects/items on map
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_map_structure(
        self,
        map_name: str,
        heightmap_path: Path,
        preview_path: Optional[Path] = None,
        jbeam_roads: Optional[dict] = None,  # Этап 3
        decal_roads: Optional[dict] = None,  # Этап 3
        building_items: Optional[list] = None,  # Этап 3
        mesh_files: Optional[list] = None  # Этап 3
    ) -> Path:
        """
        Create complete BeamNG.drive map structure
        
        Args:
            map_name: Internal name for the map
            heightmap_path: Path to generated heightmap PNG
            preview_path: Optional path to preview image
        
        Returns:
            Path to created ZIP file
        """
        print(f"📦 Creating BeamNG.drive mod structure for '{map_name}'...")
        
        # Create temporary working directory
        temp_dir = self.output_dir / "temp" / map_name
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        levels_dir = temp_dir / "levels" / map_name
        art_dir = levels_dir / "art" / "terrains" / "main_terrain"
        
        art_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy heightmap
        shutil.copy(heightmap_path, art_dir / "heightmap.png")
        print(f"   ✅ Copied heightmap")
        
        # Generate info.json
        info_json = self._generate_info_json(map_name)
        with open(levels_dir / "info.json", "w") as f:
            json.dump(info_json, f, indent=2)
        print(f"   ✅ Generated info.json")
        
        # Generate main.level.json
        main_level_json = self._generate_main_level_json(map_name)
        with open(levels_dir / "main.level.json", "w") as f:
            json.dump(main_level_json, f, indent=2)
        print(f"   ✅ Generated main.level.json")
        
        # Generate terrain layers.json
        layers_json = self._generate_terrain_layers()
        with open(art_dir / "layers.json", "w") as f:
            json.dump(layers_json, f, indent=2)
        print(f"   ✅ Generated terrain layers.json")
        
        # Generate items.level.json
        items_json = self._generate_items_json(building_items)
        with open(levels_dir / "items.level.json", "w") as f:
            json.dump(items_json, f, indent=2)
        print(f"   ✅ Generated items.level.json")
        
        # Add roads (Этап 3)
        if decal_roads:
            decal_road_path = levels_dir / "decalRoad.json"
            with open(decal_road_path, "w") as f:
                json.dump(decal_roads, f, indent=2)
            print(f"   ✅ Generated decalRoad.json ({len(decal_roads.get('roads', []))} roads)")
        
        # Add JBeam roads (Этап 3)
        if jbeam_roads:
            jbeam_dir = levels_dir / "vehicles" / "road_network"
            jbeam_dir.mkdir(parents=True, exist_ok=True)
            jbeam_path = jbeam_dir / "roads.jbeam"
            with open(jbeam_path, "w") as f:
                json.dump(jbeam_roads, f, indent=2)
            print(f"   ✅ Generated JBeam roads ({len(jbeam_roads)} segments)")
        
        # Copy building meshes (Этап 3)
        if mesh_files:
            shapes_dir = art_dir / "shapes" / "buildings"
            shapes_dir.mkdir(parents=True, exist_ok=True)
            for mesh_file in mesh_files:
                mesh_path = Path(mesh_file)
                if mesh_path.exists():
                    shutil.copy(mesh_path, shapes_dir / mesh_path.name)
            print(f"   ✅ Copied {len(mesh_files)} building meshes")
        
        # Create ZIP archive
        zip_path = self.output_dir / f"{map_name}.zip"
        self._create_zip(temp_dir, zip_path)
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir)
        
        print(f"✅ BeamNG.drive mod created: {zip_path}")
        return zip_path
    
    def _generate_info_json(self, map_name: str) -> dict:
        """Generate info.json with map metadata"""
        return {
            "name": map_name.replace("_", " ").title(),
            "description": f"Generated by BeamNG.WorldForge from real satellite data",
            "authors": "BeamNG.WorldForge",
            "version": "1.0",
            "previews": {
                "main": f"levels/{map_name}/preview.jpg"
            },
            "difficulty": 0,
            "spawn_points": [
                {
                    "name": "Default Spawn",
                    "pos": [0, 0, 100],
                    "rot": [0, 0, 0, 1]
                }
            ]
        }
    
    def _generate_main_level_json(self, map_name: str) -> dict:
        """Generate main.level.json with level configuration"""
        return {
            "name": map_name,
            "description": "Generated terrain from satellite data",
            "levelName": map_name,
            "sun": {
                "azimuth": 0,
                "elevation": 45,
                "shadowDistance": 1000,
                "shadowSoftness": 0.15
            },
            "time": {
                "time": 0.5,
                "timeScale": 1.0,
                "play": False
            },
            "gravity": -9.81,
            "terrain": {
                "terrainFile": f"art/terrains/main_terrain/heightmap.png",
                "squareSize": 2.0,  # 2 meters per heightmap pixel
                "baseTexture": "grid512"
            },
            "weather": {
                "fogDensity": 0.001,
                "fogDensityOffset": 0,
                "cloudCover": 0.5
            }
        }
    
    def _generate_terrain_layers(self) -> dict:
        """
        Generate terrain layers configuration
        
        For MVP, we use simple default textures.
        In future stages, AI will generate custom textures.
        """
        return {
            "version": 1,
            "materials": [
                {
                    "name": "grass",
                    "internalName": "grass",
                    "diffuseMap": "art/terrains/grass_green_d.dds",
                    "normalMap": "art/terrains/grass_green_n.dds",
                    "detailMap": "art/terrains/grass_green_d.dds",
                    "detailSize": 4.0
                },
                {
                    "name": "dirt",
                    "internalName": "dirt",
                    "diffuseMap": "art/terrains/dirt_brown_d.dds",
                    "normalMap": "art/terrains/dirt_brown_n.dds",
                    "detailMap": "art/terrains/dirt_brown_d.dds",
                    "detailSize": 4.0
                },
                {
                    "name": "rock",
                    "internalName": "rock",
                    "diffuseMap": "art/terrains/rock_grey_d.dds",
                    "normalMap": "art/terrains/rock_grey_n.dds",
                    "detailMap": "art/terrains/rock_grey_d.dds",
                    "detailSize": 4.0
                }
            ],
            "layers": [
                {
                    "name": "base_layer",
                    "material": "grass",
                    "minHeight": -1000,
                    "maxHeight": 1000,
                    "minSlope": 0,
                    "maxSlope": 90
                }
            ]
        }
    
    def _generate_items_json(self, building_items: Optional[list] = None) -> dict:
        """
        Generate items.level.json with map objects
        
        Args:
            building_items: List of building items from Этап 3
        """
        items = building_items if building_items else []
        
        return {
            "version": 1,
            "items": items
        }
    
    def _create_zip(self, source_dir: Path, output_zip: Path):
        """Create ZIP archive from directory"""
        print(f"🗜️  Creating ZIP archive...")
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through all files in source directory
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    # Get relative path
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        print(f"   ✅ ZIP created: {output_zip.stat().st_size / 1024 / 1024:.2f} MB")


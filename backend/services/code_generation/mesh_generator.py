"""Procedural 3D building mesh generation"""

import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import numpy as np

from .code_generator import CodeGenerator
from .prompts import get_building_mesh_prompt


class MeshGenerator:
    """
    Generate procedural 3D building meshes
    """
    
    def __init__(self, code_generator: Optional[CodeGenerator] = None):
        """
        Initialize mesh generator
        
        Args:
            code_generator: CodeGenerator instance (creates new if None)
        """
        self.code_gen = code_generator or CodeGenerator()
        print(f"🏢 Mesh Generator initialized")
    
    async def generate_building_meshes(
        self,
        buildings_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate meshes for multiple buildings
        
        Args:
            buildings_data: List of building dicts from vector extraction
                [{"footprint": [[lat, lon], ...], "height": 15.0, "type": "residential"}, ...]
        
        Returns:
            List of DAE XML strings
        """
        print(f"🏢 Generating meshes for {len(buildings_data)} buildings...")
        
        meshes = []
        
        for idx, building in enumerate(buildings_data[:50], 1):  # Limit to 50 for performance
            print(f"   Processing building {idx}/{min(len(buildings_data), 50)}...")
            
            try:
                mesh_dae = await self.generate_single_building(
                    footprint=building.get("footprint", []),
                    height=building.get("height", 10.0),
                    building_type=building.get("type", "residential"),
                    building_id=idx
                )
                
                meshes.append(mesh_dae)
                
            except Exception as e:
                print(f"⚠️  Failed to generate building {idx}: {e}")
                # Try fallback
                try:
                    mesh_dae = self._create_fallback_mesh(
                        footprint=building.get("footprint", []),
                        height=building.get("height", 10.0),
                        building_id=idx
                    )
                    meshes.append(mesh_dae)
                except:
                    continue
        
        print(f"✅ Building meshes generated: {len(meshes)}")
        return meshes
    
    async def generate_single_building(
        self,
        footprint: List[Tuple[float, float]],
        height: float,
        building_type: str = "residential",
        building_id: int = 1
    ) -> str:
        """
        Generate mesh for a single building
        
        Args:
            footprint: List of (lat, lon) coordinates forming polygon
            height: Building height in meters
            building_type: Type (residential, commercial, industrial)
            building_id: Unique ID
        
        Returns:
            Collada DAE XML string
        """
        if len(footprint) < 3:
            raise ValueError("Footprint must have at least 3 points")
        
        # Style based on type
        style_map = {
            "residential": "traditional",
            "commercial": "modern",
            "industrial": "utilitarian",
            "warehouse": "industrial"
        }
        style = style_map.get(building_type.lower(), "modern")
        
        # Generate prompt
        prompt = get_building_mesh_prompt(
            footprint=footprint[:10],  # Limit points for prompt size
            height=height,
            building_type=building_type,
            style=style
        )
        
        # Generate via AI
        try:
            dae_xml = await self.code_gen.generate_xml(prompt)
            
            # Basic validation
            if self._validate_dae(dae_xml):
                return dae_xml
            else:
                print(f"⚠️  Generated DAE invalid, using fallback")
                return self._create_fallback_mesh(footprint, height, building_id)
                
        except Exception as e:
            print(f"⚠️  AI generation failed: {e}, using fallback")
            return self._create_fallback_mesh(footprint, height, building_id)
    
    def _create_fallback_mesh(
        self,
        footprint: List[Tuple[float, float]],
        height: float,
        building_id: int
    ) -> str:
        """
        Create fallback mesh procedurally (simple extrusion)
        
        Args:
            footprint: Building footprint polygon
            height: Building height
            building_id: Building ID
        
        Returns:
            DAE XML string
        """
        print(f"   Creating procedural mesh fallback...")
        
        # Simplify footprint if too complex
        if len(footprint) > 8:
            # Sample every nth point
            n = len(footprint) // 6
            footprint = footprint[::n]
        
        # Convert to 3D vertices (floor and ceiling)
        vertices_floor = []
        vertices_ceiling = []
        
        for lat, lon in footprint:
            # Convert lat/lon to local XYZ (simplified)
            x = lon * 111000
            y = lat * 111000
            z = 0.0
            
            vertices_floor.append((x, y, z))
            vertices_ceiling.append((x, y, z + height))
        
        # Create triangles (simple fan triangulation)
        triangles = []
        num_verts = len(footprint)
        
        # Floor (pointing down)
        for i in range(1, num_verts - 1):
            triangles.append((0, i+1, i))  # Reversed winding for down face
        
        # Ceiling (pointing up)
        base_idx = num_verts
        for i in range(1, num_verts - 1):
            triangles.append((base_idx, base_idx + i, base_idx + i + 1))
        
        # Walls
        for i in range(num_verts):
            next_i = (i + 1) % num_verts
            
            # Two triangles per wall quad
            v0 = i
            v1 = next_i
            v2 = next_i + num_verts
            v3 = i + num_verts
            
            triangles.append((v0, v1, v2))
            triangles.append((v0, v2, v3))
        
        # Generate DAE XML
        dae = self._create_dae_xml(
            vertices_floor + vertices_ceiling,
            triangles,
            building_id
        )
        
        return dae
    
    def _create_dae_xml(
        self,
        vertices: List[Tuple[float, float, float]],
        triangles: List[Tuple[int, int, int]],
        building_id: int
    ) -> str:
        """
        Create Collada DAE XML from vertices and triangles
        
        Args:
            vertices: List of (x, y, z) vertices
            triangles: List of (v1, v2, v3) triangle indices
            building_id: Building ID
        
        Returns:
            DAE XML string
        """
        # Flatten vertices
        positions = []
        for x, y, z in vertices:
            positions.extend([x, y, z])
        
        positions_str = " ".join(str(p) for p in positions)
        
        # Flatten triangles
        indices = []
        for v1, v2, v3 in triangles:
            indices.extend([v1, v2, v3])
        
        indices_str = " ".join(str(i) for i in indices)
        
        # Build XML
        dae_template = f'''<?xml version="1.0" encoding="UTF-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <contributor>
      <authoring_tool>BeamNG.WorldForge AI</authoring_tool>
    </contributor>
    <created>2025-10-21T00:00:00Z</created>
    <modified>2025-10-21T00:00:00Z</modified>
    <unit meter="1.0" name="meter"/>
    <up_axis>Z_UP</up_axis>
  </asset>
  <library_geometries>
    <geometry id="building_{building_id}_mesh" name="Building{building_id}">
      <mesh>
        <source id="building_{building_id}_positions">
          <float_array id="building_{building_id}_positions_array" count="{len(positions)}">{positions_str}</float_array>
          <technique_common>
            <accessor source="#building_{building_id}_positions_array" count="{len(vertices)}" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="building_{building_id}_vertices">
          <input semantic="POSITION" source="#building_{building_id}_positions"/>
        </vertices>
        <triangles count="{len(triangles)}" material="building_material">
          <input semantic="VERTEX" source="#building_{building_id}_vertices" offset="0"/>
          <p>{indices_str}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="Building{building_id}" name="Building{building_id}">
        <instance_geometry url="#building_{building_id}_mesh"/>
      </node>
    </visual_scene>
  </library_visual_scenes>
  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>'''
        
        return dae_template
    
    def _validate_dae(self, dae_xml: str) -> bool:
        """
        Validate DAE XML structure
        
        Args:
            dae_xml: DAE XML string
        
        Returns:
            True if valid
        """
        try:
            root = ET.fromstring(dae_xml)
            
            # Check for required elements
            if root.tag != "{http://www.collada.org/2005/11/COLLADASchema}COLLADA":
                return False
            
            # Check for geometry library
            geom_lib = root.find(".//{http://www.collada.org/2005/11/COLLADASchema}library_geometries")
            if geom_lib is None:
                return False
            
            print(f"✅ DAE validation passed")
            return True
            
        except Exception as e:
            print(f"⚠️  DAE validation failed: {e}")
            return False
    
    def save_mesh(self, dae_xml: str, output_path: Path):
        """
        Save DAE mesh to file
        
        Args:
            dae_xml: DAE XML string
            output_path: Output file path (.dae)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(dae_xml)
        
        print(f"💾 Mesh saved: {output_path}")
    
    async def close(self):
        """Close resources"""
        await self.code_gen.close()


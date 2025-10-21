"""JBeam road generation from vector data"""

import json
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from .code_generator import CodeGenerator
from .prompts import get_jbeam_prompt


class JBeamGenerator:
    """
    Generate BeamNG.drive JBeam roads from vector data
    """
    
    def __init__(self, code_generator: Optional[CodeGenerator] = None):
        """
        Initialize JBeam generator
        
        Args:
            code_generator: CodeGenerator instance (creates new if None)
        """
        self.code_gen = code_generator or CodeGenerator()
        print(f"🛣️  JBeam Generator initialized")
    
    async def generate_road_network(
        self,
        roads_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate JBeam for entire road network
        
        Args:
            roads_data: List of road dicts from vector extraction
                [{"centerline": [[lat, lon], ...], "width": 10.0, "type": "highway"}, ...]
        
        Returns:
            Complete JBeam structure with all roads
        """
        print(f"🛣️  Generating JBeam for {len(roads_data)} roads...")
        
        complete_jbeam = {}
        
        for idx, road in enumerate(roads_data, 1):
            print(f"   Processing road {idx}/{len(roads_data)}...")
            
            try:
                road_jbeam = await self.generate_single_road(
                    centerline=road.get("centerline", []),
                    width=road.get("width", 8.0),
                    road_type=road.get("type", "residential"),
                    segment_id=idx
                )
                
                # Merge into complete structure
                complete_jbeam.update(road_jbeam)
                
            except Exception as e:
                print(f"⚠️  Failed to generate road {idx}: {e}")
                # Continue with other roads
                continue
        
        print(f"✅ JBeam network generated: {len(complete_jbeam)} road segments")
        return complete_jbeam
    
    async def generate_single_road(
        self,
        centerline: List[Tuple[float, float]],
        width: float,
        road_type: str = "residential",
        segment_id: int = 1
    ) -> Dict[str, Any]:
        """
        Generate JBeam for a single road
        
        Args:
            centerline: List of (lat, lon) coordinates
            width: Road width in meters
            road_type: Type of road (highway, primary, residential, dirt)
            segment_id: Unique ID for this segment
        
        Returns:
            JBeam dict for this road
        """
        if len(centerline) < 2:
            raise ValueError("Centerline must have at least 2 points")
        
        # Determine surface type from road type
        surface_map = {
            "highway": "asphalt",
            "primary": "asphalt",
            "secondary": "asphalt",
            "residential": "asphalt",
            "dirt": "dirt",
            "gravel": "gravel"
        }
        surface = surface_map.get(road_type.lower(), "asphalt")
        
        # Generate prompt
        prompt = get_jbeam_prompt(
            centerline=centerline,
            width=width,
            road_type=road_type,
            surface=surface,
            segment_id=segment_id
        )
        
        # Generate JBeam via AI
        try:
            jbeam_data = await self.code_gen.generate_json(prompt)
            
            # Validate
            is_valid = await self.code_gen.validate_jbeam(jbeam_data)
            
            if not is_valid:
                print(f"⚠️  Generated JBeam failed validation, using fallback")
                jbeam_data = self._create_fallback_jbeam(
                    centerline, width, road_type, segment_id
                )
            
            return jbeam_data
            
        except Exception as e:
            print(f"⚠️  AI generation failed: {e}, using fallback")
            return self._create_fallback_jbeam(
                centerline, width, road_type, segment_id
            )
    
    def _create_fallback_jbeam(
        self,
        centerline: List[Tuple[float, float]],
        width: float,
        road_type: str,
        segment_id: int
    ) -> Dict[str, Any]:
        """
        Create fallback JBeam without AI (procedural generation)
        
        Args:
            centerline: Road centerline
            width: Road width
            road_type: Road type
            segment_id: Segment ID
        
        Returns:
            Basic JBeam structure
        """
        print(f"   Creating procedural JBeam fallback...")
        
        # Sample centerline (take every nth point to reduce nodes)
        sample_rate = max(1, len(centerline) // 20)  # Max 20 nodes
        sampled = centerline[::sample_rate]
        
        # Ensure we have last point
        if sampled[-1] != centerline[-1]:
            sampled.append(centerline[-1])
        
        # Create nodes
        nodes = [["id", "posX", "posY", "posZ"]]
        for i, (lat, lon) in enumerate(sampled):
            # Convert lat/lon to local XYZ (simplified - just use as-is)
            # In real implementation, would convert to BeamNG coordinate system
            node_id = f"n{segment_id}_{i}"
            x = lon * 111000  # Rough meters conversion
            y = lat * 111000
            z = 0.0  # Flat road (would use heightmap in reality)
            nodes.append([node_id, x, y, z])
        
        # Create beams (connect consecutive nodes)
        beams = [["id1", "id2"]]
        for i in range(len(sampled) - 1):
            id1 = f"n{segment_id}_{i}"
            id2 = f"n{segment_id}_{i+1}"
            beams.append([id1, id2])
        
        # Determine friction
        friction = 0.9 if "asphalt" in road_type.lower() else 0.65
        
        jbeam = {
            f"road_segment_{segment_id}": {
                "information": {
                    "name": f"{road_type.title()} Road #{segment_id}",
                    "authors": "BeamNG.WorldForge (Procedural)"
                },
                "slotType": "road_segment",
                "nodes": nodes,
                "beams": beams,
                "friction": friction,
                "surfaceType": road_type
            }
        }
        
        return jbeam
    
    def save_jbeam(self, jbeam_data: Dict[str, Any], output_path: Path):
        """
        Save JBeam to file
        
        Args:
            jbeam_data: JBeam dict
            output_path: Output file path (.jbeam)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(jbeam_data, f, indent=2)
        
        print(f"💾 JBeam saved: {output_path}")
    
    async def close(self):
        """Close resources"""
        await self.code_gen.close()


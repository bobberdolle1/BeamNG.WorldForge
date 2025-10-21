"""Prompts for AI code generation - qwen3-coder"""

# JBeam road generation prompt
JBEAM_ROAD_PROMPT = """
Generate BeamNG.drive JBeam code for a road segment.

Input road data:
- Centerline coordinates: {centerline}
- Width: {width} meters
- Road type: {road_type}
- Surface: {surface_type}

Requirements:
1. Create nodes along the centerline with appropriate spacing (every 5-10 meters)
2. Generate beams connecting the nodes for road structure
3. Add physics properties:
   - friction: 0.85-0.95 for asphalt, 0.6-0.7 for dirt
   - damping: 50-100
   - spring: 1000-2000
   - deform: minimal for roads
4. Include road edge nodes for proper collision
5. Optimize node count (don't exceed 100 nodes per segment)

Return ONLY valid JBeam JSON in this exact format:
{{
  "road_segment_{segment_id}": {{
    "information": {{
      "name": "{road_name}",
      "authors": "BeamNG.WorldForge AI"
    }},
    "slotType": "road_segment",
    "nodes": [
      ["id", "posX", "posY", "posZ"],
      ["n1", x1, y1, z1],
      ["n2", x2, y2, z2]
    ],
    "beams": [
      ["id1", "id2"],
      ["n1", "n2"]
    ],
    "friction": {friction},
    "surfaceType": "{surface_type}"
  }}
}}

IMPORTANT:
- Use ONLY JSON format, no markdown, no explanations
- All coordinates must be numbers (float)
- Node IDs must be strings starting with 'n'
- Ensure proper JSON syntax (commas, brackets)
"""

# 3D Building mesh generation prompt  
BUILDING_MESH_PROMPT = """
Generate a procedural 3D building mesh in Collada DAE format for BeamNG.drive.

Input building data:
- Footprint polygon: {footprint}
- Height: {height} meters
- Building type: {building_type}
- Style: {style}

Requirements:
1. Extrude the footprint polygon vertically to the specified height
2. Create walls by connecting floor and ceiling vertices
3. Add a roof:
   - Flat roof for commercial/industrial
   - Pitched roof for residential
4. Generate appropriate vertex positions, normals, and UV coordinates
5. Keep polygon count under 500 triangles (optimize for game performance)
6. Use proper Collada DAE XML structure

Building details based on type:
- Residential: Add window openings (placeholder quads), pitched roof
- Commercial: Larger windows, flat roof, modern style
- Industrial: Minimal windows, utilitarian, flat roof

Return ONLY valid Collada DAE XML (no markdown, no explanations).

Start with:
<?xml version="1.0" encoding="UTF-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">

Include:
- <asset> section
- <library_geometries> with building mesh
- <library_visual_scenes> for placement
- Proper vertex data, normals, UVs
- Triangle indices

Keep it simple and valid!
"""

# Lua script generation for traffic
TRAFFIC_SCRIPT_PROMPT = """
Generate a Lua script for BeamNG.drive AI traffic system.

Input data:
- Road network: {road_count} roads
- Spawn points: {spawn_points}
- Traffic density: {density}

Requirements:
1. Create traffic spawn function
2. Define AI vehicle waypoints from road centerlines
3. Set appropriate speeds based on road types
4. Implement basic traffic rules (stop at intersections, follow lanes)
5. Optimize for performance (limit active AI count)

Return valid Lua script with these functions:
- onInit() - Initialize traffic system
- spawnVehicle(position, route) - Spawn AI vehicle
- updateTraffic(dt) - Update all traffic
- onUnload() - Cleanup

Use BeamNG.drive API:
- spawn.spawnVehicle()
- ai.setMode()
- ai.driveInLane()

Return ONLY the Lua code, no markdown, no explanations.
"""

# Material definition JSON
MATERIAL_JSON_PROMPT = """
Generate BeamNG.drive material definitions for map objects.

Requirements:
1. Road materials (asphalt, concrete, dirt)
2. Building materials (brick, concrete, glass, metal)
3. Proper texture paths
4. PBR properties (roughness, metalness)

Return valid JSON with this structure:
{{
  "materials": [
    {{
      "name": "material_name",
      "mapTo": "texture_file.dds",
      "colorMap": "diffuse_texture.dds",
      "normalMap": "normal_texture.dds",
      "roughness": 0.7,
      "metalness": 0.0,
      "friction": 0.9
    }}
  ]
}}

Include common materials for:
- Roads: asphalt_road, concrete_road, dirt_road
- Buildings: brick_wall, concrete_wall, glass_window, metal_roof

Return ONLY valid JSON.
"""

# decalRoad.json generation
DECAL_ROAD_JSON_PROMPT = """
Generate BeamNG.drive decalRoad.json for road network.

Input road data: {road_data}

Requirements:
1. Convert vector road centerlines to decal road format
2. Set appropriate width and texture
3. Configure proper edge falloff
4. Add road markings (lanes, center line)

DecalRoad format:
{{
  "roads": [
    {{
      "name": "road_001",
      "drivability": 1.0,
      "lanes": [
        {{
          "width": {width},
          "material": "road_asphalt"
        }}
      ],
      "nodes": [
        {{
          "pos": [x, y, z],
          "width": w,
          "offset": 0
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON for BeamNG decalRoad system.
"""


def get_jbeam_prompt(centerline, width, road_type="residential", surface="asphalt", segment_id=1):
    """Generate JBeam road prompt"""
    friction = 0.9 if surface == "asphalt" else 0.65
    
    return JBEAM_ROAD_PROMPT.format(
        centerline=centerline[:20],  # Limit to first 20 points
        width=width,
        road_type=road_type,
        surface_type=surface,
        segment_id=segment_id,
        road_name=f"{road_type.title()} Road #{segment_id}",
        friction=friction
    )


def get_building_mesh_prompt(footprint, height, building_type="residential", style="modern"):
    """Generate building mesh prompt"""
    return BUILDING_MESH_PROMPT.format(
        footprint=footprint,
        height=height,
        building_type=building_type,
        style=style
    )


def get_traffic_script_prompt(road_count, spawn_points, density="medium"):
    """Generate traffic Lua script prompt"""
    return TRAFFIC_SCRIPT_PROMPT.format(
        road_count=road_count,
        spawn_points=spawn_points,
        density=density
    )


def get_material_json_prompt():
    """Generate material JSON prompt"""
    return MATERIAL_JSON_PROMPT


def get_decal_road_prompt(road_data):
    """Generate decalRoad.json prompt"""
    return DECAL_ROAD_JSON_PROMPT.format(road_data=road_data)


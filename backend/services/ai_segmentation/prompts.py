"""Predefined prompts for AI segmentation tasks"""

# Road extraction prompt
ROAD_EXTRACTION_PROMPT = """
Analyze this satellite/aerial image and identify all roads, streets, and paths.

For each road segment, provide:
1. Road type (highway, primary_road, secondary_road, residential_street, dirt_path)
2. Centerline coordinates (sequence of [latitude, longitude] points forming the road path)
3. Estimated width in meters
4. Surface type (asphalt, concrete, gravel, dirt) if determinable
5. Confidence level (0.0 to 1.0)

Return ONLY a valid JSON array (no explanations):
[
  {
    "type": "highway",
    "centerline": [[37.7749, -122.4194], [37.7750, -122.4195], ...],
    "width": 15.0,
    "surface": "asphalt",
    "confidence": 0.95
  }
]

Guidelines:
- Be precise with coordinate sequences
- Only include clearly visible roads
- Higher confidence for well-defined roads
- Include at least 2 points per road segment
"""

# Building extraction prompt
BUILDING_EXTRACTION_PROMPT = """
Analyze this satellite/aerial image and identify all buildings.

For each building, provide:
1. Building type (residential, commercial, industrial, warehouse, other)
2. Footprint polygon (closed sequence of corner coordinates)
3. Estimated height in meters (use shadows/context if visible)
4. Roof type (flat, pitched, unknown) if determinable
5. Confidence level (0.0 to 1.0)

Return ONLY a valid JSON array:
[
  {
    "type": "residential",
    "footprint": [[37.7749, -122.4194], [37.7749, -122.4193], [37.7748, -122.4193], [37.7748, -122.4194]],
    "height": 10.0,
    "roof_type": "pitched",
    "confidence": 0.88
  }
]

Guidelines:
- Polygon must be closed (first point = last point)
- Minimum 4 corners for rectangular buildings
- Height estimation from shadows (north-facing shadows)
- Higher confidence for clear, isolated buildings
"""

# Water body extraction
WATER_EXTRACTION_PROMPT = """
Identify all water bodies in this satellite image (rivers, lakes, ponds, oceans).

For each water body, provide:
1. Type (river, lake, pond, ocean, reservoir)
2. Boundary polygon or centerline (for rivers)
3. Approximate area in square meters (for lakes/ponds)
4. Flow direction (for rivers, if determinable)
5. Confidence level

Return ONLY valid JSON array:
[
  {
    "type": "lake",
    "boundary": [[lat, lon], ...],
    "area": 50000.0,
    "confidence": 0.92
  }
]

Characteristics:
- Water appears darker/blue in satellite imagery
- Rivers have elongated shapes with flow direction
- Lakes/ponds have irregular closed boundaries
"""

# Forest/vegetation extraction
FOREST_EXTRACTION_PROMPT = """
Identify forested and vegetated areas in this satellite image.

For each vegetation area, provide:
1. Type (dense_forest, sparse_forest, grassland, agricultural)
2. Boundary polygon
3. Density level (high, medium, low)
4. Estimated tree coverage percentage
5. Confidence level

Return ONLY valid JSON array:
[
  {
    "type": "dense_forest",
    "boundary": [[lat, lon], ...],
    "density": "high",
    "tree_coverage": 85.0,
    "confidence": 0.87
  }
]

Visual characteristics:
- Green/dark green areas indicate vegetation
- Uniform texture suggests managed forests
- Varied texture suggests natural forests
- Agricultural areas show geometric patterns
"""

# Parking lot extraction
PARKING_EXTRACTION_PROMPT = """
Identify parking lots and parking areas in this satellite image.

For each parking area, provide:
1. Type (surface_lot, structure, street_parking)
2. Boundary polygon
3. Estimated capacity (number of spaces)
4. Layout pattern (grid, angled, parallel)
5. Confidence level

Return ONLY valid JSON array:
[
  {
    "type": "surface_lot",
    "boundary": [[lat, lon], ...],
    "capacity": 50,
    "layout": "grid",
    "confidence": 0.78
  }
]

Identifying features:
- Regular geometric patterns
- Lighter colored surfaces (asphalt/concrete)
- Adjacent to commercial buildings
- Visible parking space markings (high resolution)
"""

# Multi-class segmentation prompt
MULTI_CLASS_SEGMENTATION_PROMPT = """
Perform comprehensive segmentation of this satellite/aerial image.

Identify and classify ALL visible features into these categories:
- roads (all types)
- buildings (all types)
- water (rivers, lakes, oceans)
- forest (trees, vegetation)
- parking (lots, structures)
- bare_ground (dirt, sand, rock)
- other (any other significant features)

For each detected feature, provide:
1. Class name
2. Geometry (polygon, polyline, or point)
3. Specific subtype
4. Relevant attributes
5. Confidence level

Return as JSON object with arrays per class:
{
  "roads": [
    {
      "type": "highway",
      "geometry": {"type": "LineString", "coordinates": [[lat, lon], ...]},
      "width": 15.0,
      "confidence": 0.95
    }
  ],
  "buildings": [
    {
      "type": "residential",
      "geometry": {"type": "Polygon", "coordinates": [[[lat, lon], ...]]},
      "height": 10.0,
      "confidence": 0.88
    }
  ],
  "water": [...],
  "forest": [...],
  "parking": [...],
  "bare_ground": [...],
  "other": [...]
}

Be thorough and precise. Include all clearly identifiable features.
"""

# Quality assessment prompt
QUALITY_ASSESSMENT_PROMPT = """
Assess the quality and characteristics of this satellite/aerial image for map generation.

Analyze:
1. Image resolution (approximate GSD in meters/pixel)
2. Cloud coverage percentage
3. Image clarity (excellent, good, fair, poor)
4. Shadows presence (none, minimal, moderate, heavy)
5. Seasonal indicators (vegetation state, snow, etc.)
6. Overall suitability for automated feature extraction (0.0 to 1.0)

Return as JSON:
{
  "resolution_gsd": 0.5,
  "cloud_coverage": 5.0,
  "clarity": "good",
  "shadows": "minimal",
  "season": "summer",
  "suitability_score": 0.85,
  "notes": "High quality image, suitable for detailed extraction"
}
"""


# Helper function to get prompt by task
def get_prompt(task: str) -> str:
    """
    Get segmentation prompt by task name
    
    Args:
        task: Task name (roads, buildings, water, forest, parking, multi_class, quality)
    
    Returns:
        Prompt string
    """
    prompts = {
        "roads": ROAD_EXTRACTION_PROMPT,
        "buildings": BUILDING_EXTRACTION_PROMPT,
        "water": WATER_EXTRACTION_PROMPT,
        "forest": FOREST_EXTRACTION_PROMPT,
        "parking": PARKING_EXTRACTION_PROMPT,
        "multi_class": MULTI_CLASS_SEGMENTATION_PROMPT,
        "quality": QUALITY_ASSESSMENT_PROMPT,
    }
    
    return prompts.get(task, MULTI_CLASS_SEGMENTATION_PROMPT)


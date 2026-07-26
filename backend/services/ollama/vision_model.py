"""Vision model interface for Ollama"""

from typing import Any

import numpy as np

from .client import OllamaClient
from .json_parsing import extract_json, normalise_segmentation


class VisionModel:
    """Interface for Ollama vision models (e.g., qwen3-vl)"""
    
    def __init__(
        self,
        model_name: str = "qwen3-vl:235b-cloud",
        client: OllamaClient | None = None
    ):
        """
        Initialize vision model
        
        Args:
            model_name: Name of the vision model
            client: Ollama client instance (creates new if None)
        """
        self.model_name = model_name
        self.client = client or OllamaClient()
        
        print(f"👁️  Vision model initialized: {model_name}")
    
    async def analyze_image(
        self,
        image: np.ndarray,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> str:
        """
        Analyze image with custom prompt
        
        Args:
            image: RGB image as numpy array (H, W, 3)
            prompt: Analysis prompt
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum response tokens
        
        Returns:
            Model response text
        """
        # Encode image to base64
        image_b64 = self.client.encode_numpy_to_base64(image)
        
        # Generate response
        result = await self.client.generate(
            model=self.model_name,
            prompt=prompt,
            images=[image_b64],
            options={
                "temperature": temperature,
                "num_predict": max_tokens
            }
        )
        
        return result.get("response", "")
    
    async def segment_satellite_image(
        self,
        image: np.ndarray,
        classes: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Segment satellite image into different classes
        
        Args:
            image: Satellite RGB image (H, W, 3)
            classes: List of classes to identify (default: roads, buildings, water, forest, parking)
        
        Returns:
            Segmentation results as dict with detected features
        """
        if classes is None:
            classes = ["roads", "buildings", "water", "forest", "parking"]
        
        prompt = self._create_segmentation_prompt(classes)
        
        print("🔍 Analyzing satellite image for segmentation...")
        print(f"   Image size: {image.shape}")
        print(f"   Classes: {', '.join(classes)}")
        
        # Get analysis from model
        response_text = await self.analyze_image(
            image=image,
            prompt=prompt,
            temperature=0.1  # Low temperature for more consistent results
        )
        
        # Parse response into structured data
        segmentation_data = self._parse_segmentation_response(response_text, classes)
        
        print("✅ Segmentation complete")
        for cls, features in segmentation_data.items():
            print(f"   {cls}: {len(features)} features detected")
        
        return segmentation_data
    
    async def extract_roads(self, image: np.ndarray) -> list[dict[str, Any]]:
        """
        Extract road network from satellite image
        
        Args:
            image: Satellite image
        
        Returns:
            List of road segments with coordinates
        """
        prompt = """
Analyze this satellite image and identify all roads and streets.

For each road segment, provide:
1. Type (highway, primary road, secondary road, residential street, path)
2. Approximate centerline coordinates (as a path of points)
3. Width estimation (in meters)
4. Confidence level (0.0 to 1.0)

Return the results as a JSON array with this structure:
[
  {
    "type": "highway",
    "coordinates": [[lat1, lon1], [lat2, lon2], ...],
    "width": 15.0,
    "confidence": 0.95
  },
  ...
]

Be precise with coordinates. Only include clearly visible roads.
"""
        
        response = await self.analyze_image(image, prompt)
        
        # Extract JSON from response
        roads = self._extract_json_from_response(response)
        
        return roads if isinstance(roads, list) else []
    
    async def extract_buildings(self, image: np.ndarray) -> list[dict[str, Any]]:
        """
        Extract building footprints from satellite image
        
        Args:
            image: Satellite image
        
        Returns:
            List of building polygons
        """
        prompt = """
Analyze this satellite image and identify all buildings.

For each building, provide:
1. Type (residential, commercial, industrial, other)
2. Footprint polygon (coordinates of corners)
3. Approximate height (in meters, if determinable from shadows)
4. Confidence level

Return as JSON array:
[
  {
    "type": "residential",
    "polygon": [[lat1, lon1], [lat2, lon2], [lat3, lon3], [lat4, lon4]],
    "height": 10.0,
    "confidence": 0.88
  },
  ...
]

Only include clearly visible buildings with well-defined boundaries.
"""
        
        response = await self.analyze_image(image, prompt)
        buildings = self._extract_json_from_response(response)
        
        return buildings if isinstance(buildings, list) else []
    
    def _create_segmentation_prompt(self, classes: list[str]) -> str:
        """Create prompt for image segmentation"""
        classes_str = ", ".join(classes)
        
        return f"""
Analyze this satellite/aerial image and identify the following features: {classes_str}.

For each feature type, provide:
1. Locations (as bounding boxes or coordinates)
2. Confidence level (0.0 to 1.0)
3. Additional characteristics

Format your response as a JSON object with this structure:
{{
  "roads": [
    {{"coordinates": [[lat, lon], ...], "type": "highway", "confidence": 0.95}}
  ],
  "buildings": [
    {{"polygon": [[lat, lon], ...], "type": "residential", "confidence": 0.87}}
  ],
  "water": [
    {{"polygon": [[lat, lon], ...], "type": "lake", "confidence": 0.92}}
  ],
  "forest": [
    {{"area": [[lat, lon], ...], "density": "high", "confidence": 0.85}}
  ],
  "parking": [
    {{"polygon": [[lat, lon], ...], "capacity": 50, "confidence": 0.78}}
  ]
}}

Be precise and only include features you can clearly identify.
"""
    
    def _parse_segmentation_response(
        self,
        response: str,
        classes: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Parse a model reply into segmentation data.

        Args:
            response: Raw model reply.
            classes: Classes that were requested.

        Returns:
            ``{class name: [feature, ...]}``, empty lists where nothing was
            detected or the reply could not be understood.
        """
        return normalise_segmentation(extract_json(response), classes)

    def _extract_json_from_response(self, response: str) -> Any:
        """
        Extract the first JSON value from a model reply.

        Kept as a thin wrapper so existing callers keep working; the logic
        lives in :mod:`services.ollama.json_parsing`, where it can be tested
        without constructing an HTTP client.
        """
        return extract_json(response)

    async def close(self):
        """Close underlying client"""
        await self.client.close()


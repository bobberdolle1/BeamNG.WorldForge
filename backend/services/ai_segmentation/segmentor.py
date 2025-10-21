"""AI-powered image segmentation using Ollama vision models"""

import numpy as np
from typing import Optional, Dict, Any, List
from pathlib import Path

from services.ollama.client import OllamaClient
from services.ollama.vision_model import VisionModel
from .prompts import get_prompt


class AISegmentor:
    """
    AI-powered segmentation of satellite images using vision models
    """
    
    def __init__(
        self,
        model_name: str = "qwen3-vl:235b-cloud",
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize AI segmentor
        
        Args:
            model_name: Ollama vision model name
            ollama_client: Existing Ollama client (creates new if None)
        """
        self.model_name = model_name
        self.vision_model = VisionModel(model_name=model_name, client=ollama_client)
        
        print(f"🎨 AI Segmentor initialized with {model_name}")
    
    async def segment_image(
        self,
        image: np.ndarray,
        tasks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Segment satellite image using AI
        
        Args:
            image: RGB satellite image (H, W, 3)
            tasks: List of segmentation tasks (default: all)
                  Options: roads, buildings, water, forest, parking
        
        Returns:
            Segmentation results dict with extracted features per class
        """
        if tasks is None:
            tasks = ["roads", "buildings", "water", "forest", "parking"]
        
        print(f"🔍 Starting AI segmentation...")
        print(f"   Tasks: {', '.join(tasks)}")
        print(f"   Image shape: {image.shape}")
        
        # Option 1: Single multi-class prompt (faster, one API call)
        if len(tasks) > 2:
            results = await self._segment_multi_class(image, tasks)
        else:
            # Option 2: Individual tasks (more precise for specific tasks)
            results = await self._segment_individual_tasks(image, tasks)
        
        print(f"✅ AI segmentation complete")
        
        return results
    
    async def _segment_multi_class(
        self,
        image: np.ndarray,
        tasks: List[str]
    ) -> Dict[str, Any]:
        """
        Perform multi-class segmentation in one go
        
        Args:
            image: Satellite image
            tasks: Task list
        
        Returns:
            Segmentation results
        """
        prompt = get_prompt("multi_class")
        
        print(f"   Using multi-class segmentation...")
        
        # Get segmentation from vision model
        results = await self.vision_model.segment_satellite_image(
            image=image,
            classes=tasks
        )
        
        return results
    
    async def _segment_individual_tasks(
        self,
        image: np.ndarray,
        tasks: List[str]
    ) -> Dict[str, Any]:
        """
        Perform segmentation task-by-task (more precise but slower)
        
        Args:
            image: Satellite image
            tasks: Task list
        
        Returns:
            Segmentation results
        """
        results = {}
        
        for task in tasks:
            print(f"   Processing task: {task}")
            
            if task == "roads":
                roads = await self.vision_model.extract_roads(image)
                results["roads"] = roads
            
            elif task == "buildings":
                buildings = await self.vision_model.extract_buildings(image)
                results["buildings"] = buildings
            
            else:
                # Use generic prompt for other tasks
                prompt = get_prompt(task)
                response_text = await self.vision_model.analyze_image(image, prompt)
                parsed = self.vision_model._extract_json_from_response(response_text)
                results[task] = parsed if isinstance(parsed, list) else []
        
        return results
    
    async def assess_image_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Assess satellite image quality for map generation
        
        Args:
            image: Satellite image
        
        Returns:
            Quality assessment dict
        """
        prompt = get_prompt("quality")
        
        response_text = await self.vision_model.analyze_image(image, prompt)
        quality_data = self.vision_model._extract_json_from_response(response_text)
        
        if isinstance(quality_data, dict):
            return quality_data
        
        # Fallback
        return {
            "suitability_score": 0.5,
            "notes": "Could not assess quality"
        }
    
    async def extract_specific_class(
        self,
        image: np.ndarray,
        class_name: str
    ) -> List[Dict[str, Any]]:
        """
        Extract only a specific class from image
        
        Args:
            image: Satellite image
            class_name: Class to extract (roads, buildings, etc.)
        
        Returns:
            List of detected features for that class
        """
        results = await self.segment_image(image, tasks=[class_name])
        return results.get(class_name, [])
    
    def get_statistics(self, segmentation_results: Dict[str, Any]) -> Dict[str, int]:
        """
        Get statistics from segmentation results
        
        Args:
            segmentation_results: Results from segment_image()
        
        Returns:
            Statistics dict with counts per class
        """
        stats = {}
        
        for class_name, features in segmentation_results.items():
            if isinstance(features, list):
                stats[class_name] = len(features)
            else:
                stats[class_name] = 0
        
        return stats
    
    async def close(self):
        """Close resources"""
        await self.vision_model.close()


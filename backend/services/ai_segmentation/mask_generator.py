"""Generate segmentation masks from AI detection results"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw
import cv2


class MaskGenerator:
    """
    Generate pixel-level segmentation masks from AI detection results
    """
    
    def __init__(self, image_size: Tuple[int, int]):
        """
        Initialize mask generator
        
        Args:
            image_size: (height, width) of output masks
        """
        self.image_size = image_size
        print(f"🎭 Mask Generator initialized: {image_size}")
    
    def generate_masks(
        self,
        segmentation_results: Dict[str, List[Dict[str, Any]]],
        bbox: List[float]
    ) -> Dict[str, np.ndarray]:
        """
        Generate binary masks for each segmentation class
        
        Args:
            segmentation_results: Results from AISegmentor
            bbox: Geographic bounding box [min_lon, min_lat, max_lon, max_lat]
        
        Returns:
            Dict of binary masks (0/255) for each class
        """
        masks = {}
        
        for class_name, features in segmentation_results.items():
            print(f"   Generating mask for: {class_name} ({len(features)} features)")
            
            mask = self._create_class_mask(features, bbox, class_name)
            masks[class_name] = mask
        
        return masks
    
    def _create_class_mask(
        self,
        features: List[Dict[str, Any]],
        bbox: List[float],
        class_name: str
    ) -> np.ndarray:
        """
        Create binary mask for a specific class
        
        Args:
            features: List of detected features
            bbox: Geographic bounding box
            class_name: Class name (for determining geometry type)
        
        Returns:
            Binary mask (0/255) as numpy array
        """
        # Create blank mask
        mask = np.zeros(self.image_size, dtype=np.uint8)
        
        # Create PIL image for drawing
        pil_mask = Image.fromarray(mask)
        draw = ImageDraw.Draw(pil_mask)
        
        for feature in features:
            # Convert geographic coordinates to pixel coordinates
            if class_name == "roads":
                self._draw_road(draw, feature, bbox)
            elif class_name == "buildings":
                self._draw_building(draw, feature, bbox)
            else:
                self._draw_polygon(draw, feature, bbox)
        
        # Convert back to numpy
        mask = np.array(pil_mask)
        
        return mask
    
    def _draw_road(
        self,
        draw: ImageDraw.Draw,
        road: Dict[str, Any],
        bbox: List[float]
    ):
        """Draw road on mask"""
        # Get centerline coordinates
        centerline = road.get("centerline") or road.get("coordinates", [])
        width = road.get("width", 10.0)  # meters
        
        if len(centerline) < 2:
            return
        
        # Convert to pixel coordinates
        pixel_coords = [
            self._geo_to_pixel(coord, bbox)
            for coord in centerline
        ]
        
        # Convert width from meters to pixels (approximate)
        # Assuming 1 degree ≈ 111km at equator
        bbox_width_degrees = bbox[2] - bbox[0]
        bbox_width_pixels = self.image_size[1]
        meters_per_pixel = (bbox_width_degrees * 111000) / bbox_width_pixels
        pixel_width = int(width / meters_per_pixel) if meters_per_pixel > 0 else 5
        pixel_width = max(pixel_width, 2)  # Minimum 2 pixels
        
        # Draw line with width
        draw.line(pixel_coords, fill=255, width=pixel_width)
    
    def _draw_building(
        self,
        draw: ImageDraw.Draw,
        building: Dict[str, Any],
        bbox: List[float]
    ):
        """Draw building footprint on mask"""
        # Get footprint polygon
        footprint = building.get("footprint") or building.get("polygon", [])
        
        if len(footprint) < 3:
            return
        
        # Convert to pixel coordinates
        pixel_polygon = [
            self._geo_to_pixel(coord, bbox)
            for coord in footprint
        ]
        
        # Draw filled polygon
        draw.polygon(pixel_polygon, fill=255, outline=255)
    
    def _draw_polygon(
        self,
        draw: ImageDraw.Draw,
        feature: Dict[str, Any],
        bbox: List[float]
    ):
        """Draw generic polygon feature on mask"""
        # Try different possible keys for polygon coordinates
        polygon = (
            feature.get("polygon") or
            feature.get("boundary") or
            feature.get("area") or
            feature.get("coordinates", [])
        )
        
        if len(polygon) < 3:
            return
        
        # Convert to pixel coordinates
        pixel_polygon = [
            self._geo_to_pixel(coord, bbox)
            for coord in polygon
        ]
        
        # Draw filled polygon
        draw.polygon(pixel_polygon, fill=255, outline=255)
    
    def _geo_to_pixel(
        self,
        geo_coord: List[float],
        bbox: List[float]
    ) -> Tuple[int, int]:
        """
        Convert geographic coordinates to pixel coordinates
        
        Args:
            geo_coord: [latitude, longitude]
            bbox: [min_lon, min_lat, max_lon, max_lat]
        
        Returns:
            (x, y) pixel coordinates
        """
        lat, lon = geo_coord
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Normalize to 0-1
        norm_x = (lon - min_lon) / (max_lon - min_lon) if max_lon != min_lon else 0.5
        norm_y = 1.0 - ((lat - min_lat) / (max_lat - min_lat)) if max_lat != min_lat else 0.5
        
        # Scale to image size
        pixel_x = int(norm_x * self.image_size[1])
        pixel_y = int(norm_y * self.image_size[0])
        
        # Clamp to image bounds
        pixel_x = max(0, min(pixel_x, self.image_size[1] - 1))
        pixel_y = max(0, min(pixel_y, self.image_size[0] - 1))
        
        return (pixel_x, pixel_y)
    
    def refine_mask(self, mask: np.ndarray, morphology: str = "close") -> np.ndarray:
        """
        Refine mask using morphological operations
        
        Args:
            mask: Binary mask
            morphology: Operation type (close, open, dilate, erode)
        
        Returns:
            Refined mask
        """
        kernel = np.ones((3, 3), np.uint8)
        
        if morphology == "close":
            # Close small holes
            refined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        elif morphology == "open":
            # Remove small noise
            refined = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        elif morphology == "dilate":
            # Expand features
            refined = cv2.dilate(mask, kernel, iterations=1)
        elif morphology == "erode":
            # Shrink features
            refined = cv2.erode(mask, kernel, iterations=1)
        else:
            refined = mask
        
        return refined
    
    def save_masks(
        self,
        masks: Dict[str, np.ndarray],
        output_dir: str
    ):
        """
        Save masks as PNG images
        
        Args:
            masks: Dict of masks
            output_dir: Output directory path
        """
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for class_name, mask in masks.items():
            filename = output_path / f"mask_{class_name}.png"
            Image.fromarray(mask).save(filename)
            print(f"   Saved: {filename}")
    
    def create_colored_overlay(
        self,
        masks: Dict[str, np.ndarray],
        base_image: Optional[np.ndarray] = None,
        alpha: float = 0.5
    ) -> np.ndarray:
        """
        Create colored visualization of all masks
        
        Args:
            masks: Dict of binary masks
            base_image: Optional base RGB image to overlay on
            alpha: Transparency of masks (0.0 to 1.0)
        
        Returns:
            RGB visualization image
        """
        # Color map for different classes
        colors = {
            "roads": [255, 255, 0],      # Yellow
            "buildings": [255, 0, 0],    # Red
            "water": [0, 0, 255],        # Blue
            "forest": [0, 255, 0],       # Green
            "parking": [255, 128, 0],    # Orange
            "bare_ground": [165, 42, 42], # Brown
        }
        
        # Create colored overlay
        overlay = np.zeros((*self.image_size, 3), dtype=np.uint8)
        
        for class_name, mask in masks.items():
            color = colors.get(class_name, [128, 128, 128])  # Default gray
            
            # Apply color where mask is active
            for c in range(3):
                overlay[:, :, c] = np.where(mask > 0, color[c], overlay[:, :, c])
        
        # Blend with base image if provided
        if base_image is not None:
            # Resize base image if needed
            if base_image.shape[:2] != self.image_size:
                base_image = cv2.resize(base_image, (self.image_size[1], self.image_size[0]))
            
            # Blend
            result = cv2.addWeighted(base_image, 1 - alpha, overlay, alpha, 0)
        else:
            result = overlay
        
        return result


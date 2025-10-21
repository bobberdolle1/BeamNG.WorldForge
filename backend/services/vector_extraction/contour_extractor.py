"""Extract contours from segmentation masks"""

import numpy as np
import cv2
from typing import List, Tuple, Dict, Any


class ContourExtractor:
    """Extract vector contours from binary masks"""
    
    def __init__(self, simplify_tolerance: float = 2.0):
        """
        Initialize contour extractor
        
        Args:
            simplify_tolerance: Douglas-Peucker simplification tolerance
        """
        self.simplify_tolerance = simplify_tolerance
        print(f"📐 Contour Extractor initialized (tolerance: {simplify_tolerance})")
    
    def extract_contours(
        self,
        mask: np.ndarray,
        min_area: int = 100
    ) -> List[np.ndarray]:
        """
        Extract contours from binary mask
        
        Args:
            mask: Binary mask (0/255)
            min_area: Minimum contour area in pixels
        
        Returns:
            List of contours as numpy arrays
        """
        # Find contours
        contours, hierarchy = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,  # Only external contours
            cv2.CHAIN_APPROX_SIMPLE  # Compress horizontal/vertical segments
        )
        
        # Filter by area and simplify
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area >= min_area:
                # Simplify using Douglas-Peucker algorithm
                epsilon = self.simplify_tolerance
                simplified = cv2.approxPolyDP(contour, epsilon, closed=True)
                valid_contours.append(simplified)
        
        return valid_contours
    
    def contours_to_polygons(
        self,
        contours: List[np.ndarray]
    ) -> List[List[Tuple[int, int]]]:
        """
        Convert OpenCV contours to simple polygon format
        
        Args:
            contours: List of OpenCV contours
        
        Returns:
            List of polygons as list of (x, y) tuples
        """
        polygons = []
        
        for contour in contours:
            # Reshape contour from (N, 1, 2) to (N, 2)
            points = contour.reshape(-1, 2)
            
            # Convert to list of tuples
            polygon = [(int(x), int(y)) for x, y in points]
            
            polygons.append(polygon)
        
        return polygons
    
    def extract_centerlines(
        self,
        mask: np.ndarray,
        min_length: int = 50
    ) -> List[np.ndarray]:
        """
        Extract centerlines from road/path masks using skeletonization
        
        Args:
            mask: Binary mask of roads
            min_length: Minimum centerline length in pixels
        
        Returns:
            List of centerline polylines
        """
        # Skeletonize the mask to get centerlines
        from skimage.morphology import skeletonize
        
        # Convert to boolean
        binary = mask > 0
        
        # Skeletonize
        skeleton = skeletonize(binary)
        
        # Convert skeleton back to uint8
        skeleton_img = (skeleton * 255).astype(np.uint8)
        
        # Extract contours from skeleton
        contours, _ = cv2.findContours(
            skeleton_img,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filter by length
        centerlines = []
        for contour in contours:
            length = cv2.arcLength(contour, closed=False)
            
            if length >= min_length:
                # Simplify
                epsilon = self.simplify_tolerance
                simplified = cv2.approxPolyDP(contour, epsilon, closed=False)
                centerlines.append(simplified)
        
        return centerlines
    
    def extract_rectangles(
        self,
        mask: np.ndarray,
        min_area: int = 100
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int], float]]:
        """
        Extract minimum area rectangles from mask (good for buildings)
        
        Args:
            mask: Binary mask
            min_area: Minimum rectangle area
        
        Returns:
            List of rectangles as (center, size, angle)
        """
        contours = self.extract_contours(mask, min_area=min_area)
        
        rectangles = []
        for contour in contours:
            # Get minimum area rectangle
            rect = cv2.minAreaRect(contour)
            rectangles.append(rect)
        
        return rectangles
    
    def rectangle_to_polygon(
        self,
        rect: Tuple[Tuple[int, int], Tuple[int, int], float]
    ) -> List[Tuple[int, int]]:
        """
        Convert rectangle to 4-point polygon
        
        Args:
            rect: Rectangle as (center, size, angle)
        
        Returns:
            4-point polygon
        """
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        
        return [(int(x), int(y)) for x, y in box]
    
    def get_statistics(
        self,
        contours: List[np.ndarray]
    ) -> Dict[str, Any]:
        """
        Get statistics about extracted contours
        
        Args:
            contours: List of contours
        
        Returns:
            Statistics dict
        """
        if not contours:
            return {
                "count": 0,
                "total_area": 0,
                "avg_area": 0,
                "avg_perimeter": 0
            }
        
        areas = [cv2.contourArea(c) for c in contours]
        perimeters = [cv2.arcLength(c, closed=True) for c in contours]
        
        return {
            "count": len(contours),
            "total_area": sum(areas),
            "avg_area": np.mean(areas),
            "min_area": min(areas),
            "max_area": max(areas),
            "avg_perimeter": np.mean(perimeters)
        }


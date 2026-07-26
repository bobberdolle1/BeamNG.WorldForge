"""Extract contours from segmentation masks"""

from typing import Any

import cv2
import numpy as np


def _polyline_length(points: list[tuple[int, int]]) -> float:
    """Total length of a polyline in pixels."""
    return float(
        sum(
            np.hypot(b[0] - a[0], b[1] - a[1])
            for a, b in zip(points, points[1:], strict=False)
        )
    )


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
    ) -> list[np.ndarray]:
        """
        Extract contours from binary mask
        
        Args:
            mask: Binary mask (0/255)
            min_area: Minimum contour area in pixels
        
        Returns:
            List of contours as numpy arrays
        """
        # findContours requires a single-channel uint8 image; a bool mask (what
        # skimage returns) raises an unhelpful OpenCV error otherwise.
        mask = np.asarray(mask)
        if mask.dtype != np.uint8:
            mask = (mask > 0).astype(np.uint8) * 255

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
        contours: list[np.ndarray]
    ) -> list[list[tuple[int, int]]]:
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
    ) -> list[np.ndarray]:
        """
        Extract road centrelines by skeletonising the mask and tracing it.

        Args:
            mask: Binary road mask; any non-zero value counts.
            min_length: Minimum polyline length in pixels.

        Returns:
            Polylines shaped ``(N, 1, 2)``, matching OpenCV's contour layout so
            downstream code can treat them interchangeably.

        The previous implementation ran ``cv2.findContours`` over the skeleton.
        That traces an outline rather than a path, so every road came back
        running to its far end and then all the way back - an L-shaped road of
        85 skeleton pixels produced a 137-pixel retraced loop. See
        :mod:`services.vector_extraction.skeleton`.
        """
        from skimage.morphology import skeletonize

        from .skeleton import simplify_polyline, trace_skeleton

        skeleton = skeletonize(np.asarray(mask) > 0)

        centerlines = []
        for path in trace_skeleton(skeleton):
            if _polyline_length(path) < min_length:
                # Skeletons are locally two pixels wide at corners, which leaves
                # short stubs at every junction. They are noise, not roads.
                continue

            simplified = simplify_polyline(path, self.simplify_tolerance)
            if len(simplified) < 2:
                continue

            centerlines.append(np.array(simplified, dtype=np.int32).reshape(-1, 1, 2))

        return centerlines

    def measure_widths(
        self,
        mask: np.ndarray,
        polylines: list[np.ndarray]
    ) -> list[float]:
        """
        Measure the width of the masked feature under each polyline, in pixels.

        Rasterising a detection and then skeletonising it throws away its
        recorded width, and the vectoriser previously substituted a fixed
        5-pixel guess. On a 512 px image covering 6 km that turned a 9 m road
        into a 60 m one - a fifteen-lane highway.

        The width is recoverable from the mask itself: a Euclidean distance
        transform gives, for every pixel, the distance to the nearest
        background pixel. On the centreline that distance is half the local
        width, so the median along a polyline is a robust estimate that ignores
        junction bulges and frayed ends.

        Args:
            mask: The binary mask the polylines were traced from.
            polylines: Centrelines shaped ``(N, 1, 2)`` or ``(N, 2)``.

        Returns:
            One width in pixels per polyline.
        """
        binary = (np.asarray(mask) > 0).astype(np.uint8)
        distances = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

        rows, cols = distances.shape
        widths = []

        for polyline in polylines:
            points = np.asarray(polyline).reshape(-1, 2)
            samples = [
                distances[int(np.clip(y, 0, rows - 1)), int(np.clip(x, 0, cols - 1))]
                for x, y in points
            ]
            # Half-width at the centre, doubled; never below one pixel.
            widths.append(max(float(np.median(samples)) * 2.0, 1.0))

        return widths

    def extract_rectangles(
        self,
        mask: np.ndarray,
        min_area: int = 100
    ) -> list[tuple[tuple[int, int], tuple[int, int], float]]:
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
        rect: tuple[tuple[int, int], tuple[int, int], float]
    ) -> list[tuple[int, int]]:
        """
        Convert rectangle to 4-point polygon
        
        Args:
            rect: Rectangle as (center, size, angle)
        
        Returns:
            4-point polygon
        """
        # np.int0 was removed in NumPy 2.0 and this project pins NumPy 2.x, so
        # the previous `np.int0(box)` raised AttributeError on every call.
        box = cv2.boxPoints(rect)

        return [(int(round(x)), int(round(y))) for x, y in box]
    
    def get_statistics(
        self,
        contours: list[np.ndarray]
    ) -> dict[str, Any]:
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


"""Vectorize detected features into geographic coordinates"""

import numpy as np
from typing import List, Tuple, Dict, Any


class Vectorizer:
    """Convert pixel coordinates to geographic coordinates"""
    
    def __init__(self, bbox: List[float], image_size: Tuple[int, int]):
        """
        Initialize vectorizer
        
        Args:
            bbox: Geographic bounding box [min_lon, min_lat, max_lon, max_lat]
            image_size: Image size (height, width)
        """
        self.bbox = bbox
        self.image_size = image_size
        
        self.min_lon, self.min_lat, self.max_lon, self.max_lat = bbox
        self.height, self.width = image_size
        
        print(f"🗺️  Vectorizer initialized")
        print(f"   BBox: {bbox}")
        print(f"   Image size: {image_size}")
    
    def pixel_to_geo(self, pixel: Tuple[int, int]) -> Tuple[float, float]:
        """
        Convert pixel coordinates to geographic coordinates
        
        Args:
            pixel: (x, y) pixel coordinates
        
        Returns:
            (latitude, longitude)
        """
        x, y = pixel
        
        # Normalize to 0-1
        norm_x = x / self.width
        norm_y = 1.0 - (y / self.height)  # Y is inverted
        
        # Scale to geographic bounds
        lon = self.min_lon + norm_x * (self.max_lon - self.min_lon)
        lat = self.min_lat + norm_y * (self.max_lat - self.min_lat)
        
        return (lat, lon)
    
    def polygon_to_geo(
        self,
        polygon: List[Tuple[int, int]]
    ) -> List[Tuple[float, float]]:
        """
        Convert polygon from pixel to geographic coordinates
        
        Args:
            polygon: List of (x, y) pixel coordinates
        
        Returns:
            List of (latitude, longitude) coordinates
        """
        return [self.pixel_to_geo(point) for point in polygon]
    
    def contour_to_geo(
        self,
        contour: np.ndarray
    ) -> List[Tuple[float, float]]:
        """
        Convert OpenCV contour to geographic coordinates
        
        Args:
            contour: OpenCV contour (N, 1, 2) or (N, 2)
        
        Returns:
            List of (latitude, longitude) coordinates
        """
        # Reshape if needed
        if len(contour.shape) == 3:
            points = contour.reshape(-1, 2)
        else:
            points = contour
        
        # Convert each point
        geo_points = []
        for x, y in points:
            lat, lon = self.pixel_to_geo((int(x), int(y)))
            geo_points.append((lat, lon))
        
        return geo_points
    
    def vectorize_road_network(
        self,
        centerlines: List[np.ndarray],
        width_pixels: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Vectorize road centerlines to geographic coordinates
        
        Args:
            centerlines: List of centerline contours
            width_pixels: Road width in pixels (for estimation)
        
        Returns:
            List of road segments with geographic coordinates
        """
        roads = []
        
        # Estimate width in meters
        # Average: 1 degree ≈ 111km at equator
        bbox_width_degrees = self.max_lon - self.min_lon
        meters_per_pixel = (bbox_width_degrees * 111000) / self.width
        width_meters = width_pixels * meters_per_pixel
        
        for centerline in centerlines:
            geo_path = self.contour_to_geo(centerline)
            
            road = {
                "type": "road",
                "centerline": geo_path,
                "width": round(width_meters, 1),
                "confidence": 0.8  # Default confidence
            }
            
            roads.append(road)
        
        return roads
    
    def vectorize_buildings(
        self,
        polygons: List[List[Tuple[int, int]]],
        default_height: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Vectorize building footprints to geographic coordinates
        
        Args:
            polygons: List of building footprint polygons (pixel coords)
            default_height: Default building height in meters
        
        Returns:
            List of building dicts with geographic footprints
        """
        buildings = []
        
        for polygon in polygons:
            geo_polygon = self.polygon_to_geo(polygon)
            
            building = {
                "type": "building",
                "footprint": geo_polygon,
                "height": default_height,
                "confidence": 0.75
            }
            
            buildings.append(building)
        
        return buildings
    
    def vectorize_area_features(
        self,
        polygons: List[List[Tuple[int, int]]],
        feature_type: str
    ) -> List[Dict[str, Any]]:
        """
        Vectorize area features (water, forest, parking) to geographic coordinates
        
        Args:
            polygons: List of area polygons (pixel coords)
            feature_type: Type of feature (water, forest, parking)
        
        Returns:
            List of feature dicts with geographic boundaries
        """
        features = []
        
        for polygon in polygons:
            geo_polygon = self.polygon_to_geo(polygon)
            
            # Calculate approximate area
            area_pixels = self._polygon_area(polygon)
            bbox_width_degrees = self.max_lon - self.min_lon
            bbox_height_degrees = self.max_lat - self.min_lat
            
            # Approximate area in square meters
            meters_per_pixel_x = (bbox_width_degrees * 111000) / self.width
            meters_per_pixel_y = (bbox_height_degrees * 111000) / self.height
            area_sq_meters = area_pixels * meters_per_pixel_x * meters_per_pixel_y
            
            feature = {
                "type": feature_type,
                "boundary": geo_polygon,
                "area_sq_meters": round(area_sq_meters, 1),
                "confidence": 0.7
            }
            
            features.append(feature)
        
        return features
    
    def _polygon_area(self, polygon: List[Tuple[int, int]]) -> float:
        """
        Calculate polygon area using shoelace formula
        
        Args:
            polygon: List of (x, y) coordinates
        
        Returns:
            Area in square pixels
        """
        if len(polygon) < 3:
            return 0.0
        
        # Shoelace formula
        area = 0.0
        for i in range(len(polygon)):
            j = (i + 1) % len(polygon)
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        
        return abs(area) / 2.0
    
    def create_geojson(
        self,
        features: List[Dict[str, Any]],
        feature_type: str
    ) -> Dict[str, Any]:
        """
        Create GeoJSON from vectorized features
        
        Args:
            features: List of vectorized features
            feature_type: Type of features (road, building, water, etc.)
        
        Returns:
            GeoJSON FeatureCollection
        """
        geojson_features = []
        
        for feature in features:
            if feature_type == "road":
                # LineString geometry
                coordinates = [[lon, lat] for lat, lon in feature.get("centerline", [])]
                geometry = {
                    "type": "LineString",
                    "coordinates": coordinates
                }
            else:
                # Polygon geometry
                polygon_coords = feature.get("footprint") or feature.get("boundary", [])
                coordinates = [[[lon, lat] for lat, lon in polygon_coords]]
                geometry = {
                    "type": "Polygon",
                    "coordinates": coordinates
                }
            
            geojson_feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    k: v for k, v in feature.items()
                    if k not in ["centerline", "footprint", "boundary"]
                }
            }
            
            geojson_features.append(geojson_feature)
        
        return {
            "type": "FeatureCollection",
            "features": geojson_features
        }


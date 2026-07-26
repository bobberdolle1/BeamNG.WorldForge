"""Vectorize detected features into geographic coordinates."""

from typing import Any

import numpy as np

from core.geo import METERS_PER_DEGREE_LAT, meters_per_degree_lon


class Vectorizer:
    """Convert pixel coordinates to geographic coordinates"""
    
    def __init__(self, bbox: list[float], image_size: tuple[int, int]):
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

        # Ground scale, corrected for latitude. The previous code used
        # `degrees * 111000` on both axes, which is only right at the equator:
        # a degree of longitude is shorter by cos(latitude), so road widths and
        # feature areas were overstated by 21% at 38 degrees and 100% at 60.
        center_lat = (self.min_lat + self.max_lat) / 2.0
        self.meters_per_pixel_x = (
            (self.max_lon - self.min_lon) * meters_per_degree_lon(center_lat) / self.width
            if self.width
            else 0.0
        )
        self.meters_per_pixel_y = (
            (self.max_lat - self.min_lat) * METERS_PER_DEGREE_LAT / self.height
            if self.height
            else 0.0
        )
    
    def pixel_to_geo(self, pixel: tuple[int, int]) -> tuple[float, float]:
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
        polygon: list[tuple[int, int]]
    ) -> list[tuple[float, float]]:
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
    ) -> list[tuple[float, float]]:
        """
        Convert OpenCV contour to geographic coordinates
        
        Args:
            contour: OpenCV contour (N, 1, 2) or (N, 2)
        
        Returns:
            List of (latitude, longitude) coordinates
        """
        # Reshape if needed
        points = contour.reshape(-1, 2) if len(contour.shape) == 3 else contour
        
        # Convert each point
        geo_points = []
        for x, y in points:
            lat, lon = self.pixel_to_geo((int(x), int(y)))
            geo_points.append((lat, lon))
        
        return geo_points
    
    def vectorize_road_network(
        self,
        centerlines: list[np.ndarray],
        width_pixels: float | list[float] = 5,
        source_features: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Convert road centrelines to geographic coordinates.

        Args:
            centerlines: Centreline polylines in pixel coordinates.
            width_pixels: Road width in pixels - one value for all roads, or a
                per-road list from :meth:`ContourExtractor.measure_widths`.
            source_features: The original detections, whose recorded width wins
                over anything measured off the raster.

        Returns:
            Road dicts with geographic centrelines and widths in metres.

        On width: the mask is drawn at the imagery resolution, so on a 6 km
        tile rendered at 512 px one pixel is about 12 m. A 9 m road is narrower
        than a single pixel and gets clamped to the 2 px minimum, so measuring
        it back off the raster can only ever return ~24 m or more. The
        detector's own figure is used when available; the measurement is the
        fallback for roads with no matching source.
        """
        widths = (
            list(width_pixels)
            if isinstance(width_pixels, (list, tuple))
            else [float(width_pixels)] * len(centerlines)
        )
        if len(widths) != len(centerlines):
            widths = [widths[0] if widths else 5.0] * len(centerlines)

        roads = []
        for centerline, width in zip(centerlines, widths, strict=True):
            geo_path = self.contour_to_geo(centerline)
            measured = width * self.meters_per_pixel_x
            width_meters = self._inherit_width(geo_path, source_features, measured)

            roads.append(
                {
                    "type": "road",
                    "centerline": geo_path,
                    "width": round(float(width_meters), 1),
                    "confidence": 0.8,
                }
            )

        return roads

    @staticmethod
    def _inherit_width(
        centerline: list[tuple[float, float]],
        source_features: list[dict[str, Any]] | None,
        measured: float
    ) -> float:
        """Take the width of the nearest source detection, by midpoint."""
        if not source_features or not centerline:
            return measured

        midpoint = centerline[len(centerline) // 2]

        best_width = measured
        best_distance = float("inf")

        for feature in source_features:
            points = [
                point
                for point in (feature.get("centerline") or feature.get("coordinates") or [])
                if isinstance(point, (list, tuple)) and len(point) >= 2
            ]
            if not points:
                continue

            for point in points:
                distance = (float(point[0]) - midpoint[0]) ** 2 + (float(point[1]) - midpoint[1]) ** 2
                if distance < best_distance:
                    best_distance = distance
                    best_width = float(feature.get("width") or measured)

        return best_width
    
    def vectorize_buildings(
        self,
        polygons: list[list[tuple[int, int]]],
        default_height: float = 10.0,
        source_features: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Convert building footprints to geographic coordinates.

        Args:
            polygons: Footprint polygons in pixel coordinates.
            default_height: Height to use when nothing better is known.
            source_features: The original detections. Height cannot be
                recovered from a binary mask, so without these every building
                came back at ``default_height`` - a detector that reported an
                18 m block produced a 10 m one. Each footprint inherits the
                height of the nearest source detection instead.

        Returns:
            Building dicts with geographic footprints and heights in metres.
        """
        buildings = []

        for polygon in polygons:
            geo_polygon = self.polygon_to_geo(polygon)
            height = self._inherit_height(geo_polygon, source_features, default_height)

            buildings.append(
                {
                    "type": "building",
                    "footprint": geo_polygon,
                    "height": round(float(height), 1),
                    "confidence": 0.75,
                }
            )

        return buildings

    @staticmethod
    def _inherit_height(
        footprint: list[tuple[float, float]],
        source_features: list[dict[str, Any]] | None,
        default_height: float
    ) -> float:
        """Take the height of the nearest source detection, by centroid."""
        if not source_features or not footprint:
            return default_height

        center_lat = sum(point[0] for point in footprint) / len(footprint)
        center_lon = sum(point[1] for point in footprint) / len(footprint)

        best_height = default_height
        best_distance = float("inf")

        for feature in source_features:
            points = [
                point for point in (feature.get("footprint") or feature.get("polygon") or [])
                if isinstance(point, (list, tuple)) and len(point) >= 2
            ]
            if not points:
                continue

            feature_lat = sum(float(point[0]) for point in points) / len(points)
            feature_lon = sum(float(point[1]) for point in points) / len(points)
            distance = (feature_lat - center_lat) ** 2 + (feature_lon - center_lon) ** 2

            if distance < best_distance:
                best_distance = distance
                best_height = float(feature.get("height") or default_height)

        return best_height
    
    def vectorize_area_features(
        self,
        polygons: list[list[tuple[int, int]]],
        feature_type: str
    ) -> list[dict[str, Any]]:
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
            
            area_pixels = self._polygon_area(polygon)
            area_sq_meters = area_pixels * self.meters_per_pixel_x * self.meters_per_pixel_y
            
            feature = {
                "type": feature_type,
                "boundary": geo_polygon,
                "area_sq_meters": round(area_sq_meters, 1),
                "confidence": 0.7
            }
            
            features.append(feature)
        
        return features
    
    def _polygon_area(self, polygon: list[tuple[int, int]]) -> float:
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
        features: list[dict[str, Any]],
        feature_type: str
    ) -> dict[str, Any]:
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


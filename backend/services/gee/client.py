"""Google Earth Engine client for fetching satellite data"""

import ee
import os
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import requests
from io import BytesIO
from PIL import Image


def initialize_gee():
    """
    Initialize Google Earth Engine with service account credentials
    """
    # Try to get service account key path from environment
    key_path = os.getenv("GEE_SERVICE_ACCOUNT_KEY", "config/gee-key.json")
    project_id = os.getenv("GEE_PROJECT_ID")
    
    key_file = Path(key_path)
    
    if key_file.exists():
        # Initialize with service account
        credentials = ee.ServiceAccountCredentials(None, str(key_file))
        ee.Initialize(credentials, project=project_id)
        print(f"✅ GEE initialized with service account from {key_path}")
    else:
        # Try to use default authentication (for development)
        try:
            ee.Initialize()
            print("✅ GEE initialized with default credentials")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Google Earth Engine. "
                f"Please ensure you have valid credentials. Error: {e}"
            )


def get_dem_data(
    bbox: list,
    resolution: int = 30,
    dataset: str = "USGS/SRTMGL1_003"
) -> Tuple[np.ndarray, dict]:
    """
    Fetch Digital Elevation Model (DEM) data from Google Earth Engine
    
    Args:
        bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]
        resolution: Resolution in meters (default: 30m for SRTM)
        dataset: GEE dataset ID (default: SRTM 30m)
    
    Returns:
        Tuple of (elevation array, metadata dict)
    """
    print(f"📡 Fetching DEM data from {dataset}...")
    print(f"   BBox: {bbox}, Resolution: {resolution}m")
    
    # Create region geometry
    region = ee.Geometry.Rectangle(bbox)
    
    # Load DEM dataset
    dem = ee.Image(dataset)
    
    # Clip to region
    dem_clipped = dem.clip(region)
    
    # Get download URL
    url = dem_clipped.getDownloadURL({
        'scale': resolution,
        'crs': 'EPSG:4326',
        'region': region,
        'format': 'GEO_TIFF'
    })
    
    print(f"   Download URL: {url[:100]}...")
    
    # Download the image
    response = requests.get(url)
    response.raise_for_status()
    
    # Load as numpy array using GDAL via rasterio (will implement in terrain service)
    # For now, return raw bytes and metadata
    from rasterio.io import MemoryFile
    
    with MemoryFile(response.content) as memfile:
        with memfile.open() as dataset_reader:
            elevation_data = dataset_reader.read(1)  # Read first band
            metadata = {
                'bounds': dataset_reader.bounds,
                'crs': str(dataset_reader.crs),
                'transform': dataset_reader.transform,
                'width': dataset_reader.width,
                'height': dataset_reader.height,
                'nodata': dataset_reader.nodata
            }
    
    print(f"✅ DEM data fetched: {elevation_data.shape}, "
          f"range: [{np.min(elevation_data):.1f}, {np.max(elevation_data):.1f}]m")
    
    return elevation_data, metadata


def get_satellite_image(
    bbox: list,
    resolution: int = 10,
    dataset: str = "COPERNICUS/S2_SR"
) -> Tuple[np.ndarray, dict]:
    """
    Fetch RGB satellite image from Google Earth Engine
    
    Args:
        bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]
        resolution: Resolution in meters (default: 10m for Sentinel-2)
        dataset: GEE dataset ID (default: Sentinel-2 Surface Reflectance)
    
    Returns:
        Tuple of (RGB array [H, W, 3], metadata dict)
    """
    print(f"📡 Fetching satellite image from {dataset}...")
    
    # Create region geometry
    region = ee.Geometry.Rectangle(bbox)
    
    # Load image collection and get median composite
    collection = ee.ImageCollection(dataset) \
        .filterBounds(region) \
        .filterDate('2023-01-01', '2024-12-31') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Get median composite (reduces cloud artifacts)
    image = collection.median()
    
    # Select RGB bands (Sentinel-2: B4=Red, B3=Green, B2=Blue)
    rgb = image.select(['B4', 'B3', 'B2'])
    
    # Clip to region
    rgb_clipped = rgb.clip(region)
    
    # Get download URL
    url = rgb_clipped.getDownloadURL({
        'scale': resolution,
        'crs': 'EPSG:4326',
        'region': region,
        'format': 'GEO_TIFF',
        'bands': ['B4', 'B3', 'B2'],
        'min': 0,
        'max': 3000  # Typical reflectance range for Sentinel-2
    })
    
    print(f"   Download URL: {url[:100]}...")
    
    # Download the image
    response = requests.get(url)
    response.raise_for_status()
    
    # Load as numpy array
    from rasterio.io import MemoryFile
    
    with MemoryFile(response.content) as memfile:
        with memfile.open() as dataset_reader:
            # Read RGB bands
            rgb_data = dataset_reader.read([1, 2, 3])  # Shape: (3, H, W)
            rgb_data = np.transpose(rgb_data, (1, 2, 0))  # Shape: (H, W, 3)
            
            metadata = {
                'bounds': dataset_reader.bounds,
                'crs': str(dataset_reader.crs),
                'transform': dataset_reader.transform,
                'width': dataset_reader.width,
                'height': dataset_reader.height
            }
    
    print(f"✅ Satellite image fetched: {rgb_data.shape}")
    
    return rgb_data, metadata


def test_gee_connection() -> bool:
    """Test if GEE connection is working"""
    try:
        # Simple test: get image count from a small region
        point = ee.Geometry.Point([-122.4194, 37.7749])  # San Francisco
        collection = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterBounds(point) \
            .filterDate('2023-01-01', '2023-12-31')
        
        count = collection.size().getInfo()
        print(f"✅ GEE connection test passed. Found {count} images in test region.")
        return True
    except Exception as e:
        print(f"❌ GEE connection test failed: {e}")
        return False


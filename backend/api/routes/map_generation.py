"""Map generation API endpoints"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
from typing import Dict
import asyncio

from models.map_request import MapGenerationRequest, MapGenerationResponse
from models.terrain import HeightmapConfig
from services.gee.client import get_dem_data, get_satellite_image
from services.terrain.processor import TerrainProcessor
from services.export.beamng_exporter import BeamNGExporter
from services.ai_segmentation.segmentor import AISegmentor
from services.ai_segmentation.mask_generator import MaskGenerator
from services.vector_extraction.contour_extractor import ContourExtractor
from services.vector_extraction.vectorizer import Vectorizer
import json

router = APIRouter()

# In-memory storage for generation jobs (will use Redis in production)
generation_jobs: Dict[str, dict] = {}


@router.post("/generate", response_model=MapGenerationResponse)
async def generate_map(
    request: MapGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Start map generation from satellite data
    
    This endpoint initiates the map generation process and returns immediately.
    The actual generation happens in the background.
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting map generation job: {job_id}")
    print(f"   Map name: {request.name}")
    print(f"   BBox: {request.bbox.model_dump()}")
    print(f"{'='*60}\n")
    
    # Initialize job status
    generation_jobs[job_id] = {
        "status": "starting",
        "progress": 0,
        "message": "Initializing map generation...",
        "map_name": request.name,
        "error": None
    }
    
    # Start generation in background
    background_tasks.add_task(
        run_map_generation,
        job_id,
        request
    )
    
    return MapGenerationResponse(
        success=True,
        message="Map generation started",
        map_id=job_id,
        download_url=None,
        preview_url=None
    )


@router.get("/status/{job_id}")
async def get_generation_status(job_id: str):
    """Get the status of a map generation job"""
    if job_id not in generation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = generation_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "error": job.get("error")
    }
    
    # Add download URLs if completed
    if job["status"] == "completed":
        response["download_url"] = f"/api/download/{job_id}"
        response["preview_url"] = f"/api/preview/{job_id}"
    
    return response


@router.get("/download/{job_id}")
async def download_map(job_id: str):
    """Download the generated map ZIP file"""
    if job_id not in generation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = generation_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Map generation not completed yet")
    
    # Get ZIP file path
    output_dir = Path("output")
    zip_path = output_dir / f"{job['map_name']}.zip"
    
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Generated map file not found")
    
    return FileResponse(
        path=zip_path,
        filename=f"{job['map_name']}.zip",
        media_type="application/zip"
    )


@router.get("/preview/{job_id}")
async def get_preview(job_id: str):
    """Get the heightmap preview image"""
    if job_id not in generation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = generation_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Map generation not completed yet")
    
    # Get preview file path
    temp_dir = Path("temp")
    preview_path = temp_dir / f"{job['map_name']}_preview.png"
    
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview image not found")
    
    return FileResponse(
        path=preview_path,
        media_type="image/png"
    )


async def run_map_generation(job_id: str, request: MapGenerationRequest):
    """
    Run the complete map generation pipeline
    
    This is executed as a background task
    """
    try:
        # Update status
        generation_jobs[job_id].update({
            "status": "processing",
            "progress": 10,
            "message": "Fetching DEM data from Google Earth Engine..."
        })
        
        # Step 1: Get DEM data from Google Earth Engine
        bbox = request.bbox.to_ee_geometry()
        dem_data, dem_metadata = get_dem_data(
            bbox=bbox,
            resolution=request.resolution
        )
        
        # AI Segmentation (Optional - Этап 2)
        segmentation_data = None
        vector_data = None
        
        if request.use_ai_segmentation:
            generation_jobs[job_id].update({
                "progress": 20,
                "message": "🤖 Fetching satellite imagery for AI analysis..."
            })
            
            # Get RGB satellite image
            rgb_image, rgb_metadata = get_satellite_image(
                bbox=bbox,
                resolution=10  # 10m for Sentinel-2
            )
            
            generation_jobs[job_id].update({
                "progress": 25,
                "message": "🤖 AI: Analyzing image with qwen3-vl..."
            })
            
            # AI Segmentation
            try:
                segmentor = AISegmentor(model_name="qwen3-vl:235b-cloud")
                segmentation_data = await segmentor.segment_image(
                    image=rgb_image,
                    tasks=["roads", "buildings", "water", "forest"]
                )
                
                generation_jobs[job_id].update({
                    "progress": 30,
                    "message": "🤖 AI: Generating segmentation masks..."
                })
                
                # Generate masks
                mask_gen = MaskGenerator(image_size=rgb_image.shape[:2])
                masks = mask_gen.generate_masks(segmentation_data, bbox)
                
                # Save masks for preview
                mask_gen.save_masks(masks, str(temp_dir / request.name))
                
                # Create colored overlay
                overlay = mask_gen.create_colored_overlay(masks, rgb_image, alpha=0.5)
                overlay_path = temp_dir / f"{request.name}_segmentation_overlay.png"
                from PIL import Image
                Image.fromarray(overlay).save(overlay_path)
                
                generation_jobs[job_id].update({
                    "progress": 35,
                    "message": "🤖 AI: Extracting vector data..."
                })
                
                # Extract vectors
                extractor = ContourExtractor()
                vectorizer = Vectorizer(bbox=bbox, image_size=rgb_image.shape[:2])
                
                vector_data = {}
                
                # Extract roads
                if "roads" in masks:
                    road_centerlines = extractor.extract_centerlines(masks["roads"])
                    vector_data["roads"] = vectorizer.vectorize_road_network(road_centerlines)
                
                # Extract buildings
                if "buildings" in masks:
                    building_contours = extractor.extract_contours(masks["buildings"])
                    building_polygons = extractor.contours_to_polygons(building_contours)
                    vector_data["buildings"] = vectorizer.vectorize_buildings(building_polygons)
                
                # Save vector data as GeoJSON
                geojson_dir = temp_dir / request.name / "vectors"
                geojson_dir.mkdir(parents=True, exist_ok=True)
                
                for feature_type, features in vector_data.items():
                    geojson = vectorizer.create_geojson(features, feature_type)
                    geojson_path = geojson_dir / f"{feature_type}.geojson"
                    with open(geojson_path, 'w') as f:
                        json.dump(geojson, f, indent=2)
                
                # Get statistics
                stats = segmentor.get_statistics(segmentation_data)
                print(f"🤖 AI Segmentation complete:")
                for cls, count in stats.items():
                    print(f"   {cls}: {count} features")
                
                await segmentor.close()
                
            except Exception as ai_error:
                print(f"⚠️  AI Segmentation failed (continuing without AI): {ai_error}")
                # Continue without AI features - graceful degradation
                segmentation_data = None
                vector_data = None
        
        generation_jobs[job_id].update({
            "progress": 40,
            "message": "Processing terrain data..."
        })
        
        # Step 2: Process terrain
        processor = TerrainProcessor()
        terrain_data = processor.process_dem(dem_data)
        
        generation_jobs[job_id].update({
            "progress": 55,
            "message": "Generating heightmap..."
        })
        
        # Step 3: Generate heightmap
        config = HeightmapConfig(
            size=request.heightmap_size,
            bit_depth=16,
            vertical_scale=1.0,
            interpolation="bilinear"
        )
        heightmap = processor.generate_heightmap(terrain_data, config)
        
        # Save heightmap
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        heightmap_path = temp_dir / f"{request.name}_heightmap.png"
        processor.save_heightmap(heightmap, heightmap_path, bit_depth=16)
        
        generation_jobs[job_id].update({
            "progress": 75,
            "message": "Generating preview..."
        })
        
        # Generate preview
        preview_path = temp_dir / f"{request.name}_preview.png"
        processor.generate_preview(heightmap, preview_path)
        
        generation_jobs[job_id].update({
            "progress": 90,
            "message": "Creating BeamNG.drive mod structure..."
        })
        
        # Step 4: Export to BeamNG format
        exporter = BeamNGExporter(output_dir=Path("output"))
        zip_path = exporter.create_map_structure(
            map_name=request.name,
            heightmap_path=heightmap_path,
            preview_path=preview_path
        )
        
        # Complete!
        completion_message = f"Map generation completed! Download ready: {zip_path.name}"
        if request.use_ai_segmentation and vector_data:
            road_count = len(vector_data.get("roads", []))
            building_count = len(vector_data.get("buildings", []))
            completion_message += f" | AI found: {road_count} roads, {building_count} buildings"
        
        generation_jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": completion_message,
            "ai_stats": {
                "roads": len(vector_data.get("roads", [])) if vector_data else 0,
                "buildings": len(vector_data.get("buildings", [])) if vector_data else 0
            } if request.use_ai_segmentation else None
        })
        
        print(f"\n{'='*60}")
        print(f"✅ Map generation completed: {job_id}")
        print(f"   Output: {zip_path}")
        if request.use_ai_segmentation and vector_data:
            print(f"   AI Features:")
            for feature_type, features in vector_data.items():
                print(f"     - {feature_type}: {len(features)}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        # Handle errors
        error_msg = f"Map generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        generation_jobs[job_id].update({
            "status": "failed",
            "progress": 0,
            "message": "Map generation failed",
            "error": error_msg
        })
        
        # Re-raise for logging
        raise


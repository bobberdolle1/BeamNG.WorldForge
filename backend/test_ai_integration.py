"""
Test script for AI integration - Этап 2
Tests Ollama client and AI segmentation without full pipeline
"""

import asyncio
import numpy as np
from pathlib import Path

# Test imports
try:
    from services.ollama.client import OllamaClient
    from services.ollama.vision_model import VisionModel
    from services.ai_segmentation.segmentor import AISegmentor
    from services.ai_segmentation.mask_generator import MaskGenerator
    from services.vector_extraction.contour_extractor import ContourExtractor
    from services.vector_extraction.vectorizer import Vectorizer
    print("✅ All AI modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Install dependencies: pip install opencv-python scikit-image")
    exit(1)


async def test_ollama_connection():
    """Test 1: Ollama connection"""
    print("\n" + "="*60)
    print("TEST 1: Ollama Connection")
    print("="*60)
    
    try:
        client = OllamaClient()
        models = await client.list_models()
        
        print(f"✅ Connected to Ollama")
        print(f"   Available models: {len(models)}")
        for model in models[:3]:  # Show first 3
            print(f"   - {model.get('name', 'unknown')}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return False


async def test_vision_model():
    """Test 2: Vision model basic test"""
    print("\n" + "="*60)
    print("TEST 2: Vision Model")
    print("="*60)
    
    try:
        # Create simple test image
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        model = VisionModel(model_name="qwen3-vl:235b-cloud")
        
        # Simple test prompt
        response = await model.analyze_image(
            image=test_image,
            prompt="Describe this image in one word.",
            temperature=0.1
        )
        
        print(f"✅ Vision model responded")
        print(f"   Response: {response[:100]}...")
        
        await model.close()
        return True
        
    except Exception as e:
        print(f"❌ Vision model test failed: {e}")
        print("   Note: This may fail if model is not available")
        return False


async def test_segmentation_pipeline():
    """Test 3: Full segmentation pipeline"""
    print("\n" + "="*60)
    print("TEST 3: Segmentation Pipeline")
    print("="*60)
    
    try:
        # Create mock satellite image (256x256 RGB)
        print("Creating mock satellite image...")
        mock_image = np.random.randint(50, 200, (256, 256, 3), dtype=np.uint8)
        
        # Mock bbox (San Francisco area)
        bbox = [-122.44, 37.77, -122.40, 37.80]  # [min_lon, min_lat, max_lon, max_lat]
        
        # Test mask generator (without AI)
        print("\nTesting mask generator...")
        mask_gen = MaskGenerator(image_size=(256, 256))
        
        # Create mock segmentation data
        mock_seg_data = {
            "roads": [
                {
                    "centerline": [[37.775, -122.42], [37.780, -122.41]],
                    "width": 10.0
                }
            ],
            "buildings": [
                {
                    "footprint": [
                        [37.775, -122.42],
                        [37.775, -122.419],
                        [37.774, -122.419],
                        [37.774, -122.42]
                    ]
                }
            ]
        }
        
        masks = mask_gen.generate_masks(mock_seg_data, bbox)
        print(f"✅ Generated {len(masks)} masks")
        for class_name, mask in masks.items():
            print(f"   - {class_name}: {mask.shape}")
        
        # Test contour extraction
        print("\nTesting contour extraction...")
        extractor = ContourExtractor(simplify_tolerance=2.0)
        
        if "buildings" in masks:
            contours = extractor.extract_contours(masks["buildings"], min_area=10)
            print(f"✅ Extracted {len(contours)} building contours")
        
        # Test vectorization
        print("\nTesting vectorization...")
        vectorizer = Vectorizer(bbox=bbox, image_size=(256, 256))
        
        if "buildings" in masks:
            building_contours = extractor.extract_contours(masks["buildings"])
            building_polygons = extractor.contours_to_polygons(building_contours)
            vector_buildings = vectorizer.vectorize_buildings(building_polygons)
            print(f"✅ Vectorized {len(vector_buildings)} buildings")
            
            # Test GeoJSON export
            geojson = vectorizer.create_geojson(vector_buildings, "building")
            print(f"✅ Created GeoJSON with {len(geojson['features'])} features")
        
        return True
        
    except Exception as e:
        print(f"❌ Segmentation pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🧪 BeamNG.WorldForge - AI Integration Tests")
    print("Testing Этап 2 components...")
    
    results = []
    
    # Test 1: Ollama connection
    result1 = await test_ollama_connection()
    results.append(("Ollama Connection", result1))
    
    # Test 2: Vision model (only if Ollama connected)
    if result1:
        result2 = await test_vision_model()
        results.append(("Vision Model", result2))
    else:
        print("\n⏭️  Skipping vision model test (Ollama not available)")
        results.append(("Vision Model", None))
    
    # Test 3: Segmentation pipeline (always runs)
    result3 = await test_segmentation_pipeline()
    results.append(("Segmentation Pipeline", result3))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, r in results if r is True)
    total = len([r for _, r in results if r is not None])
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("\nEтап 2 integration is working correctly!")
        print("\nNext steps:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Pull the vision model: ollama pull qwen3-vl")
        print("3. Try full generation with use_ai_segmentation=True")
    else:
        print("⚠️  Some tests failed")
        print("\nTroubleshooting:")
        print("1. Install Ollama: https://ollama.ai/download")
        print("2. Start Ollama: ollama serve")
        print("3. Pull model: ollama pull qwen3-vl")
        print("4. Check backend/.env configuration")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())


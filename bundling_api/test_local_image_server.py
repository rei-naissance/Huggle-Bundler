#!/usr/bin/env python3
"""
Test script for the local diffusers image generation server.

This script tests:
1. Starting the local image server 
2. Connecting to it from the main API
3. Generating bundle images using local diffusers

Usage:
    # Start the local image server first (in another terminal):
    python local_image_server.py
    
    # Then run this test:
    python test_local_image_server.py
"""

import asyncio
import os
import sys
import time
from app.services.image_generator import generate_bundle_image, ImageGenerationError
from app.schemas.bundle import ProductIn
import httpx

def test_local_server_connection():
    """Test if the local image server is running and accessible"""
    
    print("🔌 Testing Local Image Server Connection")
    print("=" * 50)
    
    try:
        # Test health endpoint
        with httpx.Client(timeout=10) as client:
            response = client.get("http://localhost:8001/health")
            response.raise_for_status()
            
            health_data = response.json()
            print(f"✅ Server Status: {health_data.get('status')}")
            print(f"✅ Model Loaded: {health_data.get('model_loaded')}")
            print(f"✅ Device: {health_data.get('device')}")
            
            if health_data.get('model_loaded'):
                print("✅ Local image server is ready!")
                return True
            else:
                print("⚠️  Model is still loading...")
                return False
                
    except httpx.ConnectError:
        print("❌ Cannot connect to local image server at http://localhost:8001")
        print("   Make sure to start the server first with: python local_image_server.py")
        return False
    except Exception as e:
        print(f"❌ Error connecting to local server: {e}")
        return False

def test_direct_api_call():
    """Test calling the local image API directly"""
    
    print("\n📡 Testing Direct API Call")
    print("=" * 50)
    
    try:
        prompt = "Professional product photography of an iPhone and AirPods on white background, clean studio lighting, 8K"
        
        with httpx.Client(timeout=60) as client:
            print(f"📝 Prompt: {prompt[:80]}...")
            print("🎨 Generating image (this may take 10-30 seconds)...")
            
            start_time = time.time()
            response = client.post(
                "http://localhost:8001/generate-image",
                json={"prompt": prompt, "width": 512, "height": 512}
            )
            response.raise_for_status()
            
            result = response.json()
            generation_time = time.time() - start_time
            
            print(f"✅ Image generated successfully!")
            print(f"⏱️  Generation time: {generation_time:.1f} seconds")
            print(f"🔗 Image URL: {result.get('image_url')}")
            print(f"🎲 Seed used: {result.get('seed_used')}")
            
            return True
            
    except httpx.TimeoutException:
        print("❌ Request timed out (model might be loading or generation is slow)")
        return False
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

async def test_bundle_image_generation():
    """Test bundle image generation using the integrated service"""
    
    print("\n🎨 Testing Bundle Image Generation")
    print("=" * 50)
    
    # Disable mock mode to test real local API
    os.environ["USE_MOCK_IMAGES"] = "false"
    
    # Create test products
    products = [
        ProductIn(
            id="local-test-1",
            name="MacBook Air M2", 
            product_type="laptop",
            stock=5,
            tags=["laptop", "apple", "portable"]
        ),
        ProductIn(
            id="local-test-2",
            name="Magic Keyboard",
            product_type="keyboard", 
            stock=10,
            tags=["keyboard", "apple", "wireless"]
        )
    ]
    
    print(f"✅ Created {len(products)} test products")
    
    try:
        print("🎨 Generating bundle image using local diffusers...")
        print("   This will take 10-30 seconds...")
        
        start_time = time.time()
        
        image_url = await generate_bundle_image(
            bundle_name="Apple Productivity Bundle",
            products=products,
            description="Essential Apple devices for productivity"
        )
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        print()
        print("🎉 SUCCESS! Bundle image generation completed!")
        print(f"⏱️  Total generation time: {generation_time:.1f} seconds")
        print(f"🔗 Image URL: {image_url}")
        
        return True
        
    except ImageGenerationError as e:
        print(f"❌ Bundle image generation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🧪 Local Diffusers Image Generation Tests")
    print("=" * 60)
    print("Testing local Stable Diffusion setup")
    print()
    
    results = []
    
    # Test 1: Server connection
    results.append(test_local_server_connection())
    
    if not results[0]:
        print("\n⚠️  Skipping further tests - local server not available")
        print("\n📋 TO FIX:")
        print("1. Open another terminal")
        print("2. Run: python local_image_server.py")
        print("3. Wait for model to load")
        print("4. Run this test again")
        return False
    
    # Test 2: Direct API call
    results.append(test_direct_api_call())
    
    if results[1]:
        # Test 3: Integrated bundle generation
        print("\n⏳ Running async bundle test...")
        results.append(asyncio.run(test_bundle_image_generation()))
    else:
        results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "Server Connection",
        "Direct API Call", 
        "Bundle Generation"
    ]
    
    for i, (test_name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Local diffusers image generation is working perfectly!")
        print()
        print("🚀 Your setup is ready:")
        print("   • ✅ Local Stable Diffusion model loaded")
        print("   • ✅ API server running on localhost:8001") 
        print("   • ✅ Bundle integration working")
        print("   • ✅ No external API dependencies")
        print()
        print("💡 Next steps:")
        print("   1. Keep the local image server running")
        print("   2. Start your main bundling API") 
        print("   3. Use ngrok to tunnel the local server for Render deployment")
        
    else:
        print(f"\n❌ {total - passed} tests failed")
        print("Check the error messages above for troubleshooting")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
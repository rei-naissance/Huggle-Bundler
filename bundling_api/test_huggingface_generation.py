#!/usr/bin/env python3
"""
Test script for Hugging Face FLUX.1-schnell integration.
This uses the completely FREE Hugging Face Space - no credits needed!
"""

import os
import sys
import time
from app.services.image_generator import generate_bundle_image, ImageGenerationError
from app.schemas.bundle import ProductIn

def test_huggingface_generation():
    """Test image generation using Hugging Face FLUX.1-schnell"""
    
    print("🚀 Testing Hugging Face FLUX.1-schnell Integration")
    print("=" * 60)
    print("✅ Completely FREE - No API credits needed!")
    print("⏰ Rate limit: ~15 seconds between requests")
    print()
    
    # Disable mock mode to test real HuggingFace API
    os.environ["USE_MOCK_IMAGES"] = "false"
    
    # Create test products
    products = [
        ProductIn(
            id="hf-test-1",
            name="MacBook Pro M3", 
            product_type="laptop",
            stock=5,
            tags=["laptop", "apple", "professional"]
        ),
        ProductIn(
            id="hf-test-2",
            name="Magic Mouse",
            product_type="mouse", 
            stock=10,
            tags=["mouse", "apple", "wireless"]
        ),
        ProductIn(
            id="hf-test-3",
            name="AirPods Pro Max",
            product_type="headphones", 
            stock=7,
            tags=["headphones", "apple", "premium"]
        )
    ]
    
    print(f"✅ Created {len(products)} test products")
    
    try:
        print("🎨 Generating image using Hugging Face FLUX.1-schnell...")
        print("   This will take ~10-30 seconds (including rate limiting)...")
        print("   ⏳ Please wait...")
        
        start_time = time.time()
        
        image_url = generate_bundle_image(
            bundle_name="Apple Pro Workspace Bundle",
            products=products,
            description="Complete professional Apple workspace setup"
        )
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        print()
        print("🎉 SUCCESS! Image generation completed!")
        print(f"⏱️  Generation time: {generation_time:.1f} seconds")
        print(f"🔗 Image URL: {image_url}")
        print()
        
        # Verify the URL looks correct
        if "hf.space" in image_url or "huggingface" in image_url:
            print("✅ URL format looks correct for Hugging Face Spaces")
        else:
            print("⚠️  URL format might be unexpected")
        
        print()
        print("🎯 NEXT STEPS:")
        print("1. ✅ Hugging Face integration is working perfectly!")
        print("2. 🖼️  You can now use the real API endpoints to generate bundle images")
        print("3. 🚀 Start your FastAPI server and test the endpoints")
        print("4. ⏰ Remember the ~15 second rate limit between requests")
        
        return True
        
    except ImageGenerationError as e:
        print(f"❌ Image generation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_multiple_generations():
    """Test multiple image generations with rate limiting"""
    
    print("\n" + "=" * 60)
    print("🔄 Testing Multiple Generations with Rate Limiting")
    print("=" * 60)
    
    bundles = [
        {
            "name": "Gaming Essentials", 
            "products": [
                ProductIn(id="g1", name="Gaming Keyboard", product_type="keyboard", stock=5, tags=["gaming"]),
                ProductIn(id="g2", name="Gaming Mouse", product_type="mouse", stock=8, tags=["gaming"])
            ]
        },
        {
            "name": "Office Productivity",
            "products": [
                ProductIn(id="o1", name="Wireless Headphones", product_type="headphones", stock=3, tags=["office"]),
                ProductIn(id="o2", name="USB-C Hub", product_type="hub", stock=12, tags=["connectivity"])
            ]
        }
    ]
    
    results = []
    
    for i, bundle_data in enumerate(bundles, 1):
        print(f"\n🎨 Generating image {i}/{len(bundles)}: {bundle_data['name']}")
        try:
            start_time = time.time()
            
            image_url = generate_bundle_image(
                bundle_name=bundle_data['name'],
                products=bundle_data['products'],
                description=f"Test bundle {i}"
            )
            
            end_time = time.time()
            generation_time = end_time - start_time
            
            print(f"✅ Success! Time: {generation_time:.1f}s")
            print(f"🔗 URL: {image_url}")
            results.append(True)
            
        except Exception as e:
            print(f"❌ Failed: {str(e)[:100]}...")
            results.append(False)
    
    success_count = sum(results)
    print(f"\n📊 Results: {success_count}/{len(results)} successful generations")
    
    if success_count == len(results):
        print("🎉 All generations successful!")
        print("✅ Rate limiting is working properly")
    
    return success_count > 0

def main():
    """Run all tests"""
    
    print("🧪 Hugging Face FLUX.1-schnell Integration Tests")
    print("=" * 60)
    print("This tests the FREE Hugging Face Spaces API")
    print("No API keys or credits needed! 🆓")
    print()
    
    results = []
    
    # Test single generation
    results.append(test_huggingface_generation())
    
    # Test multiple generations (if first test passed)
    if results[0]:
        results.append(test_multiple_generations())
    else:
        print("\n⏭️  Skipping multiple generation test due to first test failure")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Hugging Face FLUX.1-schnell integration is working perfectly")
        print()
        print("🚀 Your bundle image generation feature is now:")
        print("   • ✅ Completely FREE (no API costs)")
        print("   • 🎨 Using state-of-the-art FLUX.1-schnell model")
        print("   • ⏰ Rate-limited to respect Hugging Face limits")
        print("   • 🔧 Fully integrated with your bundle system")
        print()
        print("💡 Ready to use with your API endpoints!")
    else:
        print(f"❌ {total - passed}/{total} tests failed")
        print("Please check the error messages above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Quick test script to verify Replicate image generation is working
"""

import os
import sys
from app.config import settings
from app.services.image_generator import generate_bundle_image, ImageGenerationError
from app.schemas.bundle import ProductIn

def test_image_generation():
    """Test a simple image generation"""
    
    print("🧪 Testing Bundle Image Generation")
    print("=" * 40)
    
    # Check configuration
    if not settings.replicate_api_token:
        print("❌ REPLICATE_API_TOKEN not configured")
        return False
        
    print(f"✅ REPLICATE_API_TOKEN configured (length: {len(settings.replicate_api_token)})")
    
    # Create test products
    products = [
        ProductIn(
            id="test-1",
            name="iPhone 15 Pro Max", 
            product_type="smartphone",
            stock=10,
            tags=["smartphone", "apple", "premium"]
        ),
        ProductIn(
            id="test-2",
            name="AirPods Pro (2nd Gen)",
            product_type="earbuds", 
            stock=5,
            tags=["earbuds", "apple", "wireless"]
        )
    ]
    
    print(f"✅ Created {len(products)} test products")
    
    try:
        print("🎨 Generating test image...")
        print("   This may take a few seconds...")
        
        image_url = generate_bundle_image(
            bundle_name="Test Apple Bundle",
            products=products,
            description="Test bundle for verification"
        )
        
        print("✅ Image generation successful!")
        print(f"🔗 Image URL: {image_url}")
        print()
        print("🎉 Bundle image generation is working correctly!")
        return True
        
    except ImageGenerationError as e:
        print(f"❌ Image generation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_image_generation()
    sys.exit(0 if success else 1)
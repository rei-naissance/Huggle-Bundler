#!/usr/bin/env python3
"""
End-to-end test of the image generation API endpoints.
Tests all the new endpoints without needing real credits (uses mock mode).
"""

import os
import sys
import json
import time
from typing import Dict, Any

# Set mock mode before importing anything else
os.environ["USE_MOCK_IMAGES"] = "true"

from app.main import app
from app.db import get_db
from app.models.bundle import Bundle
from app.schemas.bundle import ProductIn, BundleCreate
from app.repositories.bundles import create_bundle
from fastapi.testclient import TestClient


def create_test_bundle(db) -> Bundle:
    """Create a test bundle in the database"""
    
    # Create test bundle data
    test_products = [
        {
            "id": "prod-1",
            "name": "Test iPhone",
            "product_type": "smartphone", 
            "expires_on": None,
            "stock": 10,
            "tags": ["smartphone", "apple"]
        },
        {
            "id": "prod-2", 
            "name": "Test AirPods",
            "product_type": "earbuds",
            "expires_on": None,
            "stock": 5,
            "tags": ["earbuds", "apple", "wireless"]
        }
    ]
    
    # Create the bundle
    bundle_create = BundleCreate(
        store_id="test-store",
        name="Test API Bundle", 
        description="Bundle created for API testing",
        products=[ProductIn(**p) for p in test_products],
        images=[],
        stock=5
    )
    
    # Save to database
    bundle = create_bundle(db, bundle_create)
    return bundle


def test_single_bundle_image_generation():
    """Test generating an image for a single bundle"""
    
    print("🧪 Testing Single Bundle Image Generation Endpoint")
    print("-" * 50)
    
    with TestClient(app) as client:
        # Get database session
        db = next(get_db())
        
        try:
            # Create a test bundle
            bundle = create_test_bundle(db)
            print(f"✅ Created test bundle with ID: {bundle.id}")
            
            # Call the image generation endpoint
            response = client.post(f"/bundles/{bundle.id}/generate-image")
            
            print(f"📡 API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Image generation successful!")
                print(f"   Bundle ID: {data.get('bundle_id')}")
                print(f"   Image URL: {data.get('image_url')}")
                print(f"   Message: {data.get('message')}")
                
                # Verify bundle was updated in database
                updated_bundle = db.query(Bundle).filter(Bundle.id == bundle.id).first()
                if updated_bundle and updated_bundle.image_url:
                    print(f"✅ Database updated with image URL: {updated_bundle.image_url}")
                    return True
                else:
                    print("❌ Database was not updated with image URL")
                    return False
            else:
                print(f"❌ API call failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
        finally:
            db.close()


def test_batch_image_generation():
    """Test batch image generation for multiple bundles"""
    
    print("\n🧪 Testing Batch Image Generation Endpoint") 
    print("-" * 50)
    
    with TestClient(app) as client:
        db = next(get_db())
        
        try:
            # Create multiple test bundles without images
            bundles = []
            for i in range(3):
                # Modify the bundle creation to create unique bundles
                test_products = [
                    {
                        "id": f"batch-prod-{i}-1",
                        "name": f"Test Product {i}-1",
                        "product_type": "test", 
                        "expires_on": None,
                        "stock": 10,
                        "tags": ["test"]
                    },
                    {
                        "id": f"batch-prod-{i}-2", 
                        "name": f"Test Product {i}-2",
                        "product_type": "test",
                        "expires_on": None,
                        "stock": 5,
                        "tags": ["test"]
                    }
                ]
                
                bundle_create = BundleCreate(
                    store_id="test-store-batch",
                    name=f"Batch Test Bundle {i+1}", 
                    description=f"Batch bundle {i+1} for testing",
                    products=[ProductIn(**p) for p in test_products],
                    images=[],
                    stock=5
                )
                
                bundle = create_bundle(db, bundle_create)
                bundles.append(bundle)
            
            print(f"✅ Created {len(bundles)} test bundles for batch processing")
            
            # Call the batch generation endpoint
            response = client.post(
                "/bundles/generate-images/batch",
                params={
                    "store_id": "test-store-batch",
                    "limit": 5,
                    "max_concurrent": 2
                }
            )
            
            print(f"📡 Batch API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Batch image generation successful!")
                print(f"   Processed: {data.get('processed')}")
                print(f"   Updated: {data.get('updated')}")
                print(f"   Failed: {data.get('failed')}")
                print(f"   Message: {data.get('message')}")
                
                # Show some results
                results = data.get('results', {})
                for bundle_id, image_url in results.items():
                    if image_url:
                        print(f"   Bundle {bundle_id}: {image_url}")
                
                return True
            else:
                print(f"❌ Batch API call failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Batch test failed: {e}")
            return False
        finally:
            db.close()


def test_ai_recommend_with_images():
    """Test AI recommendation with image generation"""
    
    print("\n🧪 Testing AI Recommend + Generate Images Endpoint")
    print("-" * 50)
    
    with TestClient(app) as client:
        try:
            # Call the combined endpoint
            response = client.post(
                "/bundles/recommend/ai/save-with-images",
                json={
                    "store_id": "test-store-ai",
                    "num_bundles": 2
                }
            )
            
            print(f"📡 AI Recommend API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                bundles = response.json()
                print(f"✅ AI recommendation + image generation successful!")
                print(f"   Generated {len(bundles)} bundles with images")
                
                for i, bundle in enumerate(bundles):
                    print(f"   Bundle {i+1}:")
                    print(f"     Name: {bundle.get('name')}")
                    print(f"     Image URL: {bundle.get('image_url')}")
                    print(f"     Products: {len(bundle.get('products', []))}")
                
                return True
            else:
                print(f"❌ AI Recommend API call failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ AI Recommend test failed: {e}")
            return False


def main():
    """Run all endpoint tests"""
    
    print("🚀 Testing Bundle Image Generation API Endpoints")
    print("=" * 60)
    print("Using MOCK MODE - no credits needed!")
    print()
    
    results = []
    
    # Test individual endpoints
    results.append(test_single_bundle_image_generation())
    results.append(test_batch_image_generation()) 
    results.append(test_ai_recommend_with_images())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total} tests")
    if passed == total:
        print("🎉 All API endpoints are working perfectly!")
        print()
        print("💡 To use real image generation:")
        print("   1. Add credits to your Replicate account at https://replicate.com/account/billing")
        print("   2. Set USE_MOCK_IMAGES=false in your .env file") 
        print("   3. Restart your server")
        print("   4. All endpoints will automatically use real AI image generation!")
    else:
        print(f"❌ {total - passed} tests failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test script for async image generation API
"""

import asyncio
import httpx
import time
import json

BASE_URL = "http://localhost:8001"

async def test_async_image_generation():
    """Test the async image generation workflow"""
    
    print("🧪 Testing Async Image Generation")
    print("=" * 60)
    
    # Test data
    prompts = [
        "A beautiful e-commerce bundle featuring smartphone and headphones on white background",
        "Professional product photography of laptop and mouse bundle, studio lighting",
        "Coffee maker and premium coffee beans bundle, commercial photography"
    ]
    
    async with httpx.AsyncClient() as client:
        # First, check if the server is running
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Server is healthy: {health}")
            else:
                print("❌ Server health check failed")
                return
        except httpx.ConnectError:
            print("❌ Cannot connect to image server. Make sure it's running at http://localhost:8001")
            return
        
        print("\\n📸 Testing Async Generation")
        print("-" * 40)
        
        # Test async generation
        jobs = []
        for i, prompt in enumerate(prompts, 1):
            print(f"Starting job {i}: {prompt[:50]}...")
            
            start_time = time.time()
            response = await client.post(
                f"{BASE_URL}/generate-image-async",
                json={
                    "prompt": prompt,
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 4
                }
            )
            
            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data["job_id"]
                jobs.append({
                    "id": job_id,
                    "prompt": prompt,
                    "started": start_time,
                    "index": i
                })
                print(f"  ✅ Job {i} started: {job_id}")
            else:
                print(f"  ❌ Job {i} failed to start: {response.status_code}")
        
        # Monitor jobs
        print(f"\\n⏳ Monitoring {len(jobs)} jobs...")
        completed_jobs = []
        
        max_wait = 180  # 3 minutes total
        check_start = time.time()
        
        while jobs and (time.time() - check_start) < max_wait:
            for job in jobs[:]:  # Copy to avoid modification during iteration
                response = await client.get(f"{BASE_URL}/job/{job['id']}")
                if response.status_code == 200:
                    job_status = response.json()
                    status = job_status["status"]
                    
                    if status == "completed":
                        elapsed = time.time() - job["started"]
                        print(f"  ✅ Job {job['index']} completed in {elapsed:.1f}s")
                        print(f"     Image: {job_status['image_url']}")
                        completed_jobs.append(job)
                        jobs.remove(job)
                        
                    elif status == "failed":
                        elapsed = time.time() - job["started"]
                        print(f"  ❌ Job {job['index']} failed after {elapsed:.1f}s")
                        print(f"     Error: {job_status.get('error', 'Unknown error')}")
                        jobs.remove(job)
                        
                    elif status == "processing":
                        elapsed = time.time() - job["started"]
                        print(f"  🔄 Job {job['index']} processing... ({elapsed:.1f}s)")
            
            if jobs:  # Still have jobs running
                await asyncio.sleep(3)
        
        # Summary
        print("\\n📊 Results Summary")
        print("-" * 40)
        print(f"Completed: {len(completed_jobs)}")
        print(f"Still running/failed: {len(jobs)}")
        
        # Test sync generation for comparison
        print("\\n⚡ Testing Quick Sync Generation")
        print("-" * 40)
        
        sync_start = time.time()
        response = await client.post(
            f"{BASE_URL}/generate-image",
            json={
                "prompt": "Quick test: smartphone on white background",
                "width": 512,
                "height": 512,
                "num_inference_steps": 2
            }
        )
        
        if response.status_code == 200:
            sync_result = response.json()
            sync_time = time.time() - sync_start
            print(f"✅ Sync generation completed in {sync_time:.1f}s")
            print(f"   Image: {sync_result['image_url']}")
            print(f"   Generation time: {sync_result['generation_time']:.2f}s")
        else:
            print(f"❌ Sync generation failed: {response.status_code}")


def main():
    asyncio.run(test_async_image_generation())


if __name__ == "__main__":
    main()
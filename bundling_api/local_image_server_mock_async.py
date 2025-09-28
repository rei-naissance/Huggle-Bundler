#!/usr/bin/env python3
"""
Mock Async Local Image Generation Server for Demonstration

This version simulates async image generation without requiring
torch/diffusers dependencies, perfect for testing the async workflow.
"""

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict
import random
import json

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip3 install fastapi uvicorn pydantic")
    exit(1)

# Configuration
OUTPUT_DIR = Path("mock_generated_images")
OUTPUT_DIR.mkdir(exist_ok=True)
JOBS_DIR = Path("image_jobs")
JOBS_DIR.mkdir(exist_ok=True)

# Global variables
app = FastAPI(title="Mock Async Local Image Generation API", version="2.0.0-mock")
active_jobs: Dict[str, Dict] = {}


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    num_inference_steps: int = 2
    guidance_scale: float = 0.0
    width: int = 512
    height: int = 512
    seed: Optional[int] = None


class ImageGenerationResponse(BaseModel):
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    image_url: Optional[str] = None
    generation_time: Optional[float] = None
    error: Optional[str] = None


class QuickImageResponse(BaseModel):
    image_url: str
    generation_time: float
    seed_used: int


def create_mock_image(filename: str, width: int = 512, height: int = 512) -> str:
    """Create a simple colored square as mock image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a colorful mock image
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        bg_color = random.choice(colors)
        
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Add some text
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        text = "MOCK IMAGE"
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            draw.text((x, y), text, fill='white', font=font)
        
        # Add timestamp
        timestamp = f"{int(time.time())}"
        if font:
            draw.text((10, height-30), timestamp, fill='white', font=font)
        
        # Save the image
        image_path = OUTPUT_DIR / filename
        img.save(image_path, format="PNG")
        return f"http://localhost:8001/images/{filename}"
        
    except ImportError:
        # Fallback: create a simple text file as "image"
        image_path = OUTPUT_DIR / filename.replace('.png', '.txt')
        with open(image_path, 'w') as f:
            f.write(f"Mock image created at {time.time()}\n")
            f.write(f"Size: {width}x{height}\n")
            f.write("This is a mock image file (install Pillow for actual images)\n")
        return f"http://localhost:8001/images/{filename.replace('.png', '.txt')}"


async def generate_image_mock_async(job_id: str, request: ImageGenerationRequest):
    """Generate mock image asynchronously"""
    global active_jobs
    
    try:
        # Update job status
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["started_at"] = time.time()
        
        print(f"[{job_id}] Mock generating: {request.prompt[:50]}...")
        
        # Simulate generation time (2-8 seconds for demo)
        generation_time = random.uniform(2.0, 8.0)
        await asyncio.sleep(generation_time)
        
        # Create mock image
        image_filename = f"{job_id}.png"
        image_url = create_mock_image(image_filename, request.width, request.height)
        
        # Simulate occasional failures (10% chance)
        if random.random() < 0.1:
            raise Exception("Mock random failure for testing")
        
        # Update job status
        active_jobs[job_id].update({
            "status": "completed",
            "image_url": image_url,
            "generation_time": generation_time,
            "seed_used": request.seed or random.randint(0, 999999),
            "completed_at": time.time()
        })
        
        print(f"[{job_id}] Mock generated in {generation_time:.2f}s: {image_url}")
        
    except Exception as e:
        print(f"[{job_id}] Mock generation failed: {e}")
        active_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time()
        })


@app.on_event("startup")
async def startup_event():
    print("🎭 Mock image generation server started!")
    print("📝 This is a mock server that simulates async image generation")
    print("🎨 Images are simple colored squares with text (or text files)")


@app.get("/")
async def root():
    return {
        "message": "Mock Async Local Image Generation API",
        "model": "mock-diffusion-v1.0",
        "device": "mock-cpu",
        "ready": True,
        "active_jobs": len(active_jobs),
        "note": "This is a mock server for demonstration"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": True,
        "device": "mock",
        "active_jobs": len(active_jobs),
        "mock": True
    }


@app.post("/generate-image-async", response_model=ImageGenerationResponse)
async def generate_image_async_endpoint(request: ImageGenerationRequest, background_tasks: BackgroundTasks):
    """Start async image generation and return job ID"""
    
    job_id = str(uuid.uuid4())
    
    # Create job record
    active_jobs[job_id] = {
        "status": "queued",
        "prompt": request.prompt,
        "created_at": time.time()
    }
    
    # Start background generation
    background_tasks.add_task(generate_image_mock_async, job_id, request)
    
    return ImageGenerationResponse(
        job_id=job_id,
        status="queued"
    )


@app.get("/job/{job_id}", response_model=ImageGenerationResponse)
async def get_job_status(job_id: str):
    """Get status of an image generation job"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    return ImageGenerationResponse(
        job_id=job_id,
        status=job["status"],
        image_url=job.get("image_url"),
        generation_time=job.get("generation_time"),
        error=job.get("error")
    )


@app.post("/generate-image", response_model=QuickImageResponse)
async def generate_image_sync(request: ImageGenerationRequest):
    """Synchronous mock image generation"""
    
    try:
        print(f"Quick mock generation: {request.prompt[:50]}...")
        start_time = time.time()
        
        # Simulate quick generation (1-3 seconds)
        generation_time = random.uniform(1.0, 3.0)
        await asyncio.sleep(generation_time)
        
        # Create mock image
        image_filename = f"quick_{uuid.uuid4()}.png"
        image_url = create_mock_image(image_filename, request.width, request.height)
        
        actual_time = time.time() - start_time
        seed_used = request.seed or random.randint(0, 999999)
        
        print(f"Quick mock generation completed in {actual_time:.2f}s")
        
        return QuickImageResponse(
            image_url=image_url,
            generation_time=actual_time,
            seed_used=seed_used
        )
        
    except Exception as e:
        print(f"Quick mock generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/images/{filename}")
async def get_image(filename: str):
    """Serve generated images"""
    # Try PNG first, then TXT fallback
    image_path = OUTPUT_DIR / filename
    if not image_path.exists():
        # Try txt version
        txt_path = OUTPUT_DIR / filename.replace('.png', '.txt')
        if txt_path.exists():
            return FileResponse(txt_path, media_type="text/plain")
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path, media_type="image/png")


@app.get("/jobs")
async def list_jobs():
    """List all active jobs"""
    return {"active_jobs": len(active_jobs), "jobs": active_jobs}


@app.delete("/cleanup")
async def cleanup():
    """Clean up old jobs and images"""
    try:
        now = time.time()
        cleaned_jobs = 0
        cleaned_images = 0
        
        # Clean up old jobs (older than 10 minutes for demo)
        for job_id, job in list(active_jobs.items()):
            if now - job.get("created_at", now) > 600:
                del active_jobs[job_id]
                cleaned_jobs += 1
        
        # Clean up old images
        for image_file in OUTPUT_DIR.glob("*"):
            if image_file.is_file() and image_file.stat().st_mtime < now - 600:
                image_file.unlink()
                cleaned_images += 1
        
        return {
            "message": f"Cleaned up {cleaned_jobs} jobs and {cleaned_images} images"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    print("🎭 Starting Mock Async Local Image Generation Server")
    print("=" * 60)
    print("Model: mock-diffusion-v1.0 (simulation)")
    print("Device: mock-cpu")
    print("Server will be available at: http://localhost:8001")
    print("Features:")
    print("  • Async generation with job queue (simulated)")
    print("  • Mock colored image generation")
    print("  • Quick sync endpoint for testing")
    print("  • No heavy dependencies required!")
    print("Use Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        "local_image_server_mock_async:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
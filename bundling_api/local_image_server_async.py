#!/usr/bin/env python3
"""
Async Local Image Generation Server with Job Queue

This version processes image generation requests asynchronously,
allowing for longer processing times without HTTP timeouts.
"""

import asyncio
import io
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict
import json

import torch
from diffusers import DiffusionPipeline
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "stabilityai/sdxl-turbo"  # Fast model for quick generation
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("generated_images")
OUTPUT_DIR.mkdir(exist_ok=True)
JOBS_DIR = Path("image_jobs")
JOBS_DIR.mkdir(exist_ok=True)

# Global variables
app = FastAPI(title="Async Local Image Generation API", version="2.0.0")
pipeline: Optional[DiffusionPipeline] = None
active_jobs: Dict[str, Dict] = {}


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    num_inference_steps: int = 2  # Very fast with SDXL Turbo
    guidance_scale: float = 0.0   # SDXL Turbo works best with 0.0
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


async def load_model():
    """Load the diffusion model on startup"""
    global pipeline
    
    logger.info(f"Loading model {MODEL_NAME} on device {DEVICE}...")
    start_time = time.time()
    
    try:
        # Load the fast model
        pipeline = DiffusionPipeline.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            safety_checker=None,
            requires_safety_checker=False
        )
        pipeline = pipeline.to(DEVICE)
        
        # Enable optimizations
        if DEVICE == "cuda":
            pipeline.enable_attention_slicing()
            pipeline.enable_memory_efficient_attention()
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
        
        # Quick warmup
        logger.info("Warming up model...")
        warmup_start = time.time()
        _ = pipeline(
            "test", 
            num_inference_steps=1, 
            guidance_scale=0.0,
            width=256, 
            height=256
        ).images[0]
        warmup_time = time.time() - warmup_start
        logger.info(f"Model warmed up in {warmup_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


async def generate_image_async(job_id: str, request: ImageGenerationRequest):
    """Generate image asynchronously"""
    global active_jobs
    
    try:
        # Update job status
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["started_at"] = time.time()
        
        logger.info(f"[{job_id}] Generating image: {request.prompt[:50]}...")
        
        # Set seed
        generator = None
        seed_used = request.seed
        if seed_used is not None:
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        else:
            seed_used = torch.randint(0, 2**32 - 1, (1,)).item()
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        
        # Generate image
        start_time = time.time()
        result = pipeline(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            width=request.width,
            height=request.height,
            generator=generator
        )
        
        image = result.images[0]
        generation_time = time.time() - start_time
        
        # Save image
        image_filename = f"{job_id}.png"
        image_path = OUTPUT_DIR / image_filename
        image.save(image_path, format="PNG", optimize=True)
        
        image_url = f"http://localhost:8001/images/{image_filename}"
        
        # Update job status
        active_jobs[job_id].update({
            "status": "completed",
            "image_url": image_url,
            "generation_time": generation_time,
            "seed_used": seed_used,
            "completed_at": time.time()
        })
        
        logger.info(f"[{job_id}] Image generated in {generation_time:.2f}s: {image_url}")
        
    except Exception as e:
        logger.error(f"[{job_id}] Generation failed: {e}")
        active_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time()
        })


@app.on_event("startup")
async def startup_event():
    await load_model()


@app.get("/")
async def root():
    return {
        "message": "Async Local Image Generation API",
        "model": MODEL_NAME,
        "device": DEVICE,
        "ready": pipeline is not None,
        "active_jobs": len(active_jobs)
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if pipeline is not None else "loading",
        "model_loaded": pipeline is not None,
        "device": DEVICE,
        "active_jobs": len(active_jobs)
    }


@app.post("/generate-image-async", response_model=ImageGenerationResponse)
async def generate_image_async_endpoint(request: ImageGenerationRequest, background_tasks: BackgroundTasks):
    """Start async image generation and return job ID"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    job_id = str(uuid.uuid4())
    
    # Create job record
    active_jobs[job_id] = {
        "status": "queued",
        "prompt": request.prompt,
        "created_at": time.time()
    }
    
    # Start background generation
    background_tasks.add_task(generate_image_async, job_id, request)
    
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
    """Synchronous image generation (faster model, shorter timeout)"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        logger.info(f"Quick sync generation: {request.prompt[:50]}...")
        start_time = time.time()
        
        # Set seed
        generator = None
        seed_used = request.seed
        if seed_used is not None:
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        else:
            seed_used = torch.randint(0, 2**32 - 1, (1,)).item()
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        
        # Generate with very fast settings
        result = pipeline(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=min(request.num_inference_steps, 4),  # Cap at 4 steps
            guidance_scale=request.guidance_scale,
            width=min(request.width, 512),   # Cap size for speed
            height=min(request.height, 512),
            generator=generator
        )
        
        image = result.images[0]
        generation_time = time.time() - start_time
        
        # Save image
        image_filename = f"quick_{uuid.uuid4()}.png"
        image_path = OUTPUT_DIR / image_filename
        image.save(image_path, format="PNG", optimize=True)
        
        image_url = f"http://localhost:8001/images/{image_filename}"
        
        logger.info(f"Quick generation completed in {generation_time:.2f}s")
        
        return QuickImageResponse(
            image_url=image_url,
            generation_time=generation_time,
            seed_used=seed_used
        )
        
    except Exception as e:
        logger.error(f"Quick generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/images/{filename}")
async def get_image(filename: str):
    """Serve generated images"""
    image_path = OUTPUT_DIR / filename
    if not image_path.exists():
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
        
        # Clean up old jobs (older than 1 hour)
        for job_id, job in list(active_jobs.items()):
            if now - job.get("created_at", now) > 3600:
                del active_jobs[job_id]
                cleaned_jobs += 1
        
        # Clean up old images
        for image_file in OUTPUT_DIR.glob("*.png"):
            if image_file.stat().st_mtime < now - 3600:
                image_file.unlink()
                cleaned_images += 1
        
        return {
            "message": f"Cleaned up {cleaned_jobs} jobs and {cleaned_images} images"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Async Local Image Generation Server")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Device: {DEVICE}")
    print("Server will be available at: http://localhost:8001")
    print("Features:")
    print("  • Async generation with job queue")
    print("  • Fast SDXL Turbo model")
    print("  • Quick sync endpoint for testing")
    print("Use Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        "local_image_server_async:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
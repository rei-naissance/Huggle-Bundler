#!/usr/bin/env python3
"""
GPU-Optimized Async Local Image Generation Server

Optimized for RTX 3050 6GB - uses smaller, faster models that fit in VRAM.
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
from diffusers import StableDiffusionPipeline, EulerAncestralDiscreteScheduler
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - Optimized for RTX 3050 6GB

# Other models to try:
# stabilityai/stable-diffusion-2-1-base
# runwayml/stable-diffusion-v1-5
# gsdf/Counterfeit-V2.5

MODEL_NAME = "runwayml/stable-diffusion-v1-5"  # Smaller SD 1.5 model (~4GB)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("generated_images")
OUTPUT_DIR.mkdir(exist_ok=True)
JOBS_DIR = Path("image_jobs")
JOBS_DIR.mkdir(exist_ok=True)

# Global variables
app = FastAPI(title="GPU-Optimized Async Image Generation API", version="1.5.0")
pipeline: Optional[StableDiffusionPipeline] = None
active_jobs: Dict[str, Dict] = {}


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = "blurry, low quality, distorted"
    num_inference_steps: int = 15  # Good balance of speed vs quality
    guidance_scale: float = 7.5
    width: int = 512  # Standard size for SD 1.5
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
    """Load the optimized SD 1.5 model for RTX 3050"""
    global pipeline
    
    logger.info(f"Loading SD 1.5 model on {DEVICE}...")
    logger.info(f"GPU: {torch.cuda.get_device_name() if torch.cuda.is_available() else 'CPU only'}")
    
    if torch.cuda.is_available():
        logger.info(f"VRAM Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    start_time = time.time()
    
    try:
        # Load SD 1.5 with optimizations for RTX 3050
        pipeline = StableDiffusionPipeline.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            safety_checker=None,  # Disable to save VRAM
            requires_safety_checker=False
        )
        
        # Use Euler scheduler for better quality/speed balance
        pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(pipeline.scheduler.config)
        
        pipeline = pipeline.to(DEVICE)
        
        # GPU optimizations for RTX 3050
        if DEVICE == "cuda":
            # Enable memory efficient attention (saves ~20% VRAM)
            pipeline.enable_attention_slicing()
            
            # Enable CPU offloading for VAE (saves VRAM)
            pipeline.enable_sequential_cpu_offload()
            
            # Enable CUDA memory efficient attention if available
            try:
                pipeline.enable_memory_efficient_attention()
                logger.info("✅ Memory efficient attention enabled")
            except:
                logger.info("⚠️ Memory efficient attention not available")
            
            # Try to use flash attention for speed (newer GPUs)
            try:
                from diffusers.utils import is_xformers_available
                if is_xformers_available():
                    pipeline.enable_xformers_memory_efficient_attention()
                    logger.info("✅ XFormers memory efficient attention enabled")
            except:
                logger.info("⚠️ XFormers not available")
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
        
        # Quick warmup to allocate VRAM
        logger.info("Warming up model...")
        warmup_start = time.time()
        with torch.no_grad():
            _ = pipeline(
                "test", 
                num_inference_steps=1, 
                guidance_scale=1.0,
                width=256, 
                height=256,
                output_type="pil"
            ).images[0]
        warmup_time = time.time() - warmup_start
        logger.info(f"Model warmed up in {warmup_time:.2f} seconds")
        
        if DEVICE == "cuda":
            # Report VRAM usage after loading
            allocated = torch.cuda.memory_allocated() / 1024**3
            cached = torch.cuda.memory_reserved() / 1024**3
            logger.info(f"VRAM Usage: {allocated:.2f}GB allocated, {cached:.2f}GB cached")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


async def generate_image_async(job_id: str, request: ImageGenerationRequest):
    """Generate image asynchronously with GPU optimization"""
    global active_jobs
    
    try:
        # Update job status
        active_jobs[job_id]["status"] = "processing"
        active_jobs[job_id]["started_at"] = time.time()
        
        logger.info(f"[{job_id}] GPU generating: {request.prompt[:50]}...")
        
        # Set seed for reproducibility
        generator = None
        seed_used = request.seed
        if seed_used is not None:
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        else:
            seed_used = torch.randint(0, 2**32 - 1, (1,)).item()
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        
        # Generate image with optimized settings
        start_time = time.time()
        
        with torch.no_grad():  # Save memory
            result = pipeline(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                num_inference_steps=request.num_inference_steps,
                guidance_scale=request.guidance_scale,
                width=request.width,
                height=request.height,
                generator=generator,
                output_type="pil"
            )
        
        image = result.images[0]
        generation_time = time.time() - start_time
        
        # Save image
        image_filename = f"{job_id}.png"
        image_path = OUTPUT_DIR / image_filename
        image.save(image_path, format="PNG", optimize=True, quality=95)
        
        image_url = f"http://localhost:8001/images/{image_filename}"
        
        # Update job status
        active_jobs[job_id].update({
            "status": "completed",
            "image_url": image_url,
            "generation_time": generation_time,
            "seed_used": seed_used,
            "completed_at": time.time()
        })
        
        # Clear CUDA cache to prevent memory buildup
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
        
        logger.info(f"[{job_id}] GPU generated in {generation_time:.2f}s: {image_url}")
        
    except torch.cuda.OutOfMemoryError as e:
        logger.error(f"[{job_id}] GPU OOM: {e}")
        # Clear cache and retry with lower settings
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
        active_jobs[job_id].update({
            "status": "failed",
            "error": "GPU out of memory - try smaller image size or fewer inference steps",
            "completed_at": time.time()
        })
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
    gpu_info = ""
    if torch.cuda.is_available():
        gpu_info = f" | GPU: {torch.cuda.get_device_name()}"
        vram_allocated = torch.cuda.memory_allocated() / 1024**3
        vram_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        gpu_info += f" | VRAM: {vram_allocated:.1f}/{vram_total:.1f}GB"
    
    return {
        "message": "GPU-Optimized Async Image Generation API",
        "model": MODEL_NAME,
        "device": DEVICE,
        "ready": pipeline is not None,
        "active_jobs": len(active_jobs),
        "gpu_info": gpu_info
    }


@app.get("/health")
async def health_check():
    gpu_status = {}
    if torch.cuda.is_available():
        gpu_status = {
            "gpu_name": torch.cuda.get_device_name(),
            "vram_allocated_gb": round(torch.cuda.memory_allocated() / 1024**3, 2),
            "vram_total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
            "cuda_version": torch.version.cuda
        }
    
    return {
        "status": "healthy" if pipeline is not None else "loading",
        "model_loaded": pipeline is not None,
        "device": DEVICE,
        "active_jobs": len(active_jobs),
        "gpu_status": gpu_status
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
    """Synchronous image generation (fast settings)"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        logger.info(f"Quick GPU generation: {request.prompt[:50]}...")
        start_time = time.time()
        
        # Use faster settings for sync generation
        fast_steps = min(request.num_inference_steps, 10)  # Cap at 10 steps for speed
        
        # Set seed
        generator = None
        seed_used = request.seed
        if seed_used is not None:
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        else:
            seed_used = torch.randint(0, 2**32 - 1, (1,)).item()
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        
        # Generate with fast settings
        with torch.no_grad():
            result = pipeline(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                num_inference_steps=fast_steps,
                guidance_scale=request.guidance_scale,
                width=min(request.width, 512),   # Cap size for speed
                height=min(request.height, 512),
                generator=generator,
                output_type="pil"
            )
        
        image = result.images[0]
        generation_time = time.time() - start_time
        
        # Save image
        image_filename = f"quick_{uuid.uuid4()}.png"
        image_path = OUTPUT_DIR / image_filename
        image.save(image_path, format="PNG", optimize=True, quality=95)
        
        image_url = f"http://localhost:8001/images/{image_filename}"
        
        # Clear CUDA cache
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
        
        logger.info(f"Quick GPU generation completed in {generation_time:.2f}s")
        
        return QuickImageResponse(
            image_url=image_url,
            generation_time=generation_time,
            seed_used=seed_used
        )
        
    except torch.cuda.OutOfMemoryError as e:
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
        raise HTTPException(status_code=500, detail="GPU out of memory - try smaller image or fewer steps")
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
    """Clean up old jobs and images + clear GPU memory"""
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
        
        # Clear GPU memory
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        return {
            "message": f"Cleaned up {cleaned_jobs} jobs and {cleaned_images} images",
            "gpu_cache_cleared": DEVICE == "cuda"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting GPU-Optimized Async Image Generation Server")
    print("=" * 60)
    print(f"Model: {MODEL_NAME} (SD 1.5 - optimized for RTX 3050)")
    print(f"Device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("Server will be available at: http://localhost:8001")
    print("Features:")
    print("  • Async generation with job queue")
    print("  • GPU-optimized SD 1.5 model")
    print("  • Memory efficient attention")
    print("  • CPU offloading for VRAM savings")
    print("  • Automatic CUDA cache clearing")
    print("Use Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        "local_image_server_gpu_optimized:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
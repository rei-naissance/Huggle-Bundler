#!/usr/bin/env python3
"""
Local Image Generation Server using Diffusers

This server hosts a Stable Diffusion model locally and provides an API endpoint
for generating images. It's designed to run on your local machine while the main
bundling API runs on Render.

Usage:
    python local_image_server.py

The server will run on http://localhost:8001 by default.
You can then tunnel this with ngrok or similar to make it accessible from Render.
"""

import asyncio
import io
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import torch
from diffusers import DiffusionPipeline
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - Using faster model options
# MODEL_NAME = "runwayml/stable-diffusion-v1-5"          # Original (slow on CPU)
MODEL_NAME = "stabilityai/sdxl-turbo"                   # Much faster, good quality
# MODEL_NAME = "runwayml/stable-diffusion-v1-5"          # Fallback option
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("generated_images")
OUTPUT_DIR.mkdir(exist_ok=True)

# Global variables
app = FastAPI(title="Local Image Generation API", version="1.0.0")
pipeline: Optional[DiffusionPipeline] = None


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    num_inference_steps: int = 4  # Much faster with SDXL Turbo
    guidance_scale: float = 0.0   # SDXL Turbo works best with 0.0
    width: int = 512
    height: int = 512
    seed: Optional[int] = None


class ImageGenerationResponse(BaseModel):
    image_url: str
    generation_time: float
    seed_used: int


async def load_model():
    """Load the diffusion model on startup"""
    global pipeline
    
    logger.info(f"Loading model {MODEL_NAME} on device {DEVICE}...")
    start_time = time.time()
    
    try:
        # Load the model
        pipeline = DiffusionPipeline.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            safety_checker=None,  # Disable safety checker for faster loading
            requires_safety_checker=False
        )
        pipeline = pipeline.to(DEVICE)
        
        # Enable memory efficient attention if on CUDA
        if DEVICE == "cuda":
            pipeline.enable_attention_slicing()
            pipeline.enable_memory_efficient_attention()
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
        
        # Warm up the model with a test generation
        logger.info("Warming up model...")
        warmup_start = time.time()
        _ = pipeline(
            "test prompt", 
            num_inference_steps=1, 
            width=256, 
            height=256
        ).images[0]
        warmup_time = time.time() - warmup_start
        logger.info(f"Model warmed up in {warmup_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Load the model when the server starts"""
    await load_model()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Local Image Generation API is running",
        "model": MODEL_NAME,
        "device": DEVICE,
        "ready": pipeline is not None
    }


@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy" if pipeline is not None else "loading",
        "model_loaded": pipeline is not None,
        "device": DEVICE
    }


@app.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image from a text prompt using the loaded diffusion model
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        logger.info(f"Generating image for prompt: {request.prompt[:100]}...")
        start_time = time.time()
        
        # Set seed for reproducibility if provided
        generator = None
        seed_used = request.seed
        if seed_used is not None:
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        else:
            seed_used = torch.randint(0, 2**32 - 1, (1,)).item()
            generator = torch.Generator(device=DEVICE).manual_seed(seed_used)
        
        # Generate the image
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
        
        # Save the image
        image_filename = f"{uuid.uuid4()}.png"
        image_path = OUTPUT_DIR / image_filename
        image.save(image_path, format="PNG", optimize=True)
        
        # Create the URL (assuming this server is accessible at the configured URL)
        image_url = f"http://localhost:8001/images/{image_filename}"
        
        logger.info(f"Image generated successfully in {generation_time:.2f}s: {image_url}")
        
        return ImageGenerationResponse(
            image_url=image_url,
            generation_time=generation_time,
            seed_used=seed_used
        )
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@app.get("/images/{filename}")
async def get_image(filename: str):
    """Serve generated images"""
    image_path = OUTPUT_DIR / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path, media_type="image/png")


@app.get("/models")
async def list_models():
    """List available models (for future expansion)"""
    return {
        "current_model": MODEL_NAME,
        "device": DEVICE,
        "available_models": [
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/stable-diffusion-2-1",
            "stabilityai/stable-diffusion-xl-base-1.0"
        ]
    }


@app.delete("/cleanup")
async def cleanup_images():
    """Clean up old generated images"""
    try:
        count = 0
        for image_file in OUTPUT_DIR.glob("*.png"):
            if image_file.stat().st_mtime < time.time() - 3600:  # Older than 1 hour
                image_file.unlink()
                count += 1
        
        return {"message": f"Cleaned up {count} old images"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("🎨 Starting Local Image Generation Server")
    print("=" * 50)
    print(f"Model: {MODEL_NAME}")
    print(f"Device: {DEVICE}")
    print("Server will be available at: http://localhost:8001")
    print("Use Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        "local_image_server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Don't use reload with ML models
        log_level="info"
    )
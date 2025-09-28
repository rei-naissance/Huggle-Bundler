"""
Image Proxy Router

Simple proxy to serve images from the local image server via the main API.
This allows frontend to access images through public API URLs.
"""

import requests
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter()

IMAGE_SERVER_BASE_URL = "http://localhost:8001"


@router.get("/generated/{filename}")
async def serve_generated_image(filename: str):
    """
    Proxy images from local image generation server.
    
    Frontend accesses: /api/images/generated/abc123.png
    Backend proxies from: http://localhost:8001/images/abc123.png
    """
    try:
        # Validate filename (basic security)
        if not filename.endswith('.png') or '/' in filename or '..' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Get image from local server
        local_url = f"{IMAGE_SERVER_BASE_URL}/images/{filename}"
        
        response = requests.get(local_url, timeout=30)
        response.raise_for_status()
        
        # Return image with proper headers
        return Response(
            content=response.content,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch image {filename}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
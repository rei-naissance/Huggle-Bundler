"""
Mock image generation service for testing without credits.

This service generates placeholder images that look like real product bundle images
but don't require any external API calls or credits. Perfect for testing and development.
"""

import hashlib
from typing import List, Optional
from urllib.parse import quote

from ..schemas.bundle import ProductIn


def generate_mock_bundle_image(bundle_name: str, products: List[ProductIn], description: Optional[str] = None) -> str:
    """
    Generate a mock image URL for a bundle using a placeholder service.
    
    Args:
        bundle_name: Name of the bundle
        products: List of products in the bundle  
        description: Optional bundle description
        
    Returns:
        URL of a placeholder image that looks professional
    """
    # Create a deterministic hash based on bundle content so the same bundle always gets the same image
    content = f"{bundle_name}_{len(products)}"
    if products:
        content += "_" + "_".join(sorted([p.name for p in products]))
    if description:
        content += f"_{description[:50]}"
        
    # Create a hash for consistency
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    
    # Use a placeholder service that creates realistic product images
    # This service allows custom text and colors
    width = 800
    height = 600
    background_color = "f8f9fa"  # Light gray
    text_color = "2c3e50"        # Dark blue-gray
    
    # Create the text to display
    product_count = len(products)
    text_lines = [
        bundle_name,
        f"{product_count} Products",
        f"ID: {content_hash}"
    ]
    
    # Add product names if they fit
    if products and len(products) <= 3:
        text_lines.extend([p.name[:20] for p in products[:3]])
    
    # URL encode the text
    text = quote("\\n".join(text_lines))
    
    # Generate a professional looking placeholder
    mock_url = f"https://via.placeholder.com/{width}x{height}/{background_color}/{text_color}?text={text}"
    
    return mock_url


def generate_realistic_mock_image(bundle_name: str, products: List[ProductIn], description: Optional[str] = None) -> str:
    """
    Generate a more realistic looking mock image URL.
    
    This creates URLs that look like they came from a real image generation service.
    """
    # Create a deterministic hash
    content = f"{bundle_name}_{len(products)}"
    if products:
        content += "_" + "_".join(sorted([p.name for p in products]))
    
    content_hash = hashlib.md5(content.encode()).hexdigest()
    
    # Create a realistic looking URL that mimics Replicate/other services
    mock_url = f"https://replicate.delivery/pbxt/mock-{content_hash[:16]}/{content_hash}.webp"
    
    return mock_url


def is_mock_mode_enabled() -> bool:
    """
    Check if we should use mock image generation instead of real API calls.
    
    This can be controlled via environment variable or config.
    """
    import os
    return os.getenv("USE_MOCK_IMAGES", "false").lower() in ("true", "1", "yes")
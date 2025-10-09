import asyncio
import os
import time
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models.bundle import Bundle
from ..schemas.bundle import ProductIn
from .mock_image_generator import generate_realistic_mock_image, is_mock_mode_enabled

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    """Custom exception for image generation failures"""
    pass


async def call_local_image_api(prompt: str) -> Optional[str]:
    """Call the local image generation API with the given prompt (sync version)"""
    try:
        async with httpx.AsyncClient(timeout=settings.image_generation_timeout) as client:
            response = await client.post(
                f"{settings.local_image_api_url}/generate-image",
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("image_url")
            
    except httpx.TimeoutException:
        logger.error(f"Timeout calling local image API at {settings.local_image_api_url}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error calling local image API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling local image API: {e}")
        return None


async def call_local_image_api_async(prompt: str) -> Optional[Dict[str, Any]]:
    """Call the local image generation API with async job queue support"""
    try:
        # Create client with separate timeouts for different operations
        timeout = httpx.Timeout(10.0, read=150.0, write=10.0, connect=10.0)  # 150s read timeout for polling
        async with httpx.AsyncClient(timeout=timeout) as client:
            # First try async generation
            response = await client.post(
                f"{settings.local_image_api_url}/generate-image-async",
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data["job_id"]
                
                logger.info(f"Started async image generation job: {job_id}")
                
                # Poll for completion (with reasonable timeout)
                max_wait_time = 120  # 2 minutes max
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    job_response = await client.get(f"{settings.local_image_api_url}/job/{job_id}")
                    if job_response.status_code == 200:
                        job_status = job_response.json()
                        
                        if job_status["status"] == "completed":
                            logger.info(f"Async job {job_id} completed successfully")
                            return {
                                "image_url": job_status["image_url"],
                                "generation_time": job_status.get("generation_time", 0),
                                "method": "async"
                            }
                        elif job_status["status"] == "failed":
                            logger.error(f"Async job {job_id} failed: {job_status.get('error')}")
                            break
                    
                    await asyncio.sleep(2)  # Wait 2 seconds before polling again
                
                logger.warning(f"Async job {job_id} timed out, falling back to sync")
            
            # Fallback to sync generation
            logger.info("Falling back to sync image generation")
            response = await client.post(
                f"{settings.local_image_api_url}/generate-image",
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "image_url": result.get("image_url"),
                "generation_time": result.get("generation_time", 0),
                "method": "sync_fallback"
            }
            
    except httpx.TimeoutException:
        logger.error(f"Timeout calling local image API at {settings.local_image_api_url}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error calling local image API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling local image API: {e}")
        return None


def estimate_clip_tokens(text: str) -> int:
    """
    Estimate number of CLIP tokens for a given text.
    Uses a more sophisticated approach than simple word counting.
    
    Args:
        text: Input text to estimate tokens for
        
    Returns:
        Estimated number of tokens
    """
    # More accurate estimation based on CLIP tokenizer patterns:
    # - Common words: ~1 token each
    # - Numbers and technical terms: often 1-2 tokens  
    # - Special characters and punctuation: variable
    # - Subwords: longer words may be split into multiple tokens
    
    words = text.split()
    estimated_tokens = 0
    
    for word in words:
        # Strip punctuation for analysis
        clean_word = word.strip('.,;:!?"()[]')
        
        if len(clean_word) <= 3:
            # Short words: usually 1 token
            estimated_tokens += 1
        elif len(clean_word) <= 6:
            # Medium words: usually 1 token, sometimes 2
            estimated_tokens += 1
        elif len(clean_word) <= 10:
            # Longer words: often split into 2 tokens
            estimated_tokens += 2  
        else:
            # Very long words: likely split into 2-3 tokens
            estimated_tokens += 3
            
        # Add token for punctuation if present
        if word != clean_word:
            estimated_tokens += 1
    
    return estimated_tokens


def truncate_prompt_for_clip(prompt: str, max_tokens: int = 73) -> str:
    """
    Truncate prompt to fit within CLIP's token limit.
    Uses conservative limit of 73 tokens (4 token safety buffer).
    
    Args:
        prompt: Original prompt string
        max_tokens: Maximum number of tokens (default 73 for safety)
        
    Returns:
        Truncated prompt that fits within token limit
    """
    estimated_tokens = estimate_clip_tokens(prompt)
    
    if estimated_tokens <= max_tokens:
        return prompt
    
    # If over limit, progressively remove words from the end
    words = prompt.split()
    while estimated_tokens > max_tokens and len(words) > 5:  # Keep at least 5 words
        words.pop()  # Remove last word
        truncated = " ".join(words)
        estimated_tokens = estimate_clip_tokens(truncated)
    
    # Ensure proper ending
    result = " ".join(words).rstrip('.,;:') + "."
    
    if len(words) < len(prompt.split()):
        logger.warning(f"Prompt truncated from {len(prompt.split())} to {len(words)} words (estimated {estimate_clip_tokens(result)} tokens) to fit CLIP limit")
    
    return result


def get_product_category_keywords(products: List[ProductIn]) -> Dict[str, Any]:
    """
    Analyze products and return category-specific keywords and styling.
    
    Args:
        products: List of products to analyze
        
    Returns:
        Dictionary with category info, styling keywords, and composition hints
    """
    # Extract product types and tags
    categories = set()
    all_tags = set()
    
    for product in products:
        if product.product_type:
            categories.add(product.product_type.lower())
        if product.tags:
            all_tags.update([tag.lower() for tag in product.tags if tag])
    
    # Determine primary category and styling
    category_styles = {
        'electronics': {
            'style': 'sleek tech product photography',
            'background': 'clean white background',
            'lighting': 'bright professional lighting',
            'composition': 'arranged on modern surface',
            'quality': 'premium quality, sharp focus'
        },
        'food': {
            'style': 'appetizing food photography',
            'background': 'neutral background',
            'lighting': 'warm natural lighting',
            'composition': 'artfully arranged',
            'quality': 'fresh, vibrant colors'
        },
        'beverage': {
            'style': 'beverage product photography',
            'background': 'clean background',
            'lighting': 'crisp lighting with highlights',
            'composition': 'elegantly positioned',
            'quality': 'refreshing, condensation details'
        },
        'clothing': {
            'style': 'fashion product photography',
            'background': 'neutral backdrop',
            'lighting': 'soft diffused lighting',
            'composition': 'stylishly displayed',
            'quality': 'texture details, fabric quality'
        },
        'beauty': {
            'style': 'beauty product photography',
            'background': 'pristine white background',
            'lighting': 'even professional lighting',
            'composition': 'aesthetically arranged',
            'quality': 'luxurious, detailed textures'
        },
        'home': {
            'style': 'lifestyle product photography',
            'background': 'clean modern background',
            'lighting': 'natural warm lighting',
            'composition': 'thoughtfully arranged',
            'quality': 'cozy, inviting atmosphere'
        }
    }
    
    # Determine primary category
    primary_category = 'general'
    for category in ['electronics', 'food', 'beverage', 'clothing', 'beauty', 'home']:
        if any(cat in categories for cat in [category]):
            primary_category = category
            break
    
    # Check for mixed categories (different styling needed)
    is_mixed = len(categories) > 1 and primary_category != 'general'
    
    # Get styling for category
    if primary_category in category_styles:
        style_info = category_styles[primary_category].copy()
    else:
        style_info = {
            'style': 'professional product photography',
            'background': 'clean white background',
            'lighting': 'professional lighting',
            'composition': 'neatly arranged',
            'quality': 'high quality, detailed'
        }
    
    # Adjust for mixed categories
    if is_mixed:
        style_info['style'] = 'diverse product photography'
        style_info['composition'] = 'harmoniously arranged together'
    
    # Add premium modifiers for high-value items
    premium_tags = {'premium', 'luxury', 'pro', 'max', 'ultra', 'flagship'}
    if all_tags.intersection(premium_tags):
        style_info['quality'] = 'premium quality, ' + style_info['quality']
    
    return {
        'primary_category': primary_category,
        'categories': categories,
        'tags': all_tags,
        'is_mixed': is_mixed,
        'style_info': style_info
    }


def clean_product_name(name: str) -> str:
    """
    Clean product name for better prompt generation.
    
    Args:
        name: Raw product name
        
    Returns:
        Cleaned product name optimized for AI generation
    """
    if not name:
        return "product"
    
    # Remove common noise words that don't help image generation
    noise_words = {
        'pack', 'bundle', 'set', 'combo', 'deal', 'special', 'limited',
        'edition', 'version', 'model', 'brand', 'new', 'original'
    }
    
    # Clean and split
    words = name.lower().split()
    cleaned_words = []
    
    for word in words:
        # Remove noise words but keep important descriptors
        if word not in noise_words and len(word) > 1:
            cleaned_words.append(word)
    
    # Keep original if cleaning removed too much
    if len(cleaned_words) < 2:
        return name.strip()
    
    return ' '.join(cleaned_words).title()


def build_bundle_prompt(bundle_name: str, products: List[ProductIn], description: Optional[str] = None) -> str:
    """
    Build an intelligent, context-aware prompt for bundle image generation.
    Adapts style and composition based on product categories and attributes.
    
    Args:
        bundle_name: Name of the bundle
        products: List of products in the bundle
        description: Optional bundle description
        
    Returns:
        Optimized prompt string for image generation
    """
    if not products:
        return "products, professional photography, white background, high quality"
    
    # Analyze products for context-aware generation
    context = get_product_category_keywords(products)
    
    # Clean and select best product names (limit to 3-4 for clarity)
    cleaned_names = []
    for product in products[:4]:
        cleaned_name = clean_product_name(product.name)
        if cleaned_name and cleaned_name not in cleaned_names:
            cleaned_names.append(cleaned_name)
    
    if not cleaned_names:
        cleaned_names = ["products"]
    
    # Build main subject with explicit emphasis on showing ALL products
    if len(cleaned_names) == 1:
        main_subject = cleaned_names[0]
        composition_emphasis = "single product showcase"
    elif len(cleaned_names) == 2:
        main_subject = f"{cleaned_names[0]} and {cleaned_names[1]} together"
        composition_emphasis = "both products clearly visible side by side"
    elif len(cleaned_names) == 3:
        main_subject = f"{cleaned_names[0]}, {cleaned_names[1]}, and {cleaned_names[2]} all together"
        composition_emphasis = "all three products prominently displayed"
    else:
        main_subject = f"{', '.join(cleaned_names[:-1])}, and {cleaned_names[-1]} all together"
        composition_emphasis = "all products prominently displayed together"
    
    # Get style components and enhance composition for multiple products
    style_info = context['style_info']
    
    # Override composition for multiple products to ensure visibility
    if len(cleaned_names) > 1:
        if context['primary_category'] == 'electronics':
            style_info['composition'] = "arranged side by side on modern surface"
        elif context['primary_category'] == 'food':
            style_info['composition'] = "arranged together in appealing layout"
        else:
            style_info['composition'] = "arranged together prominently"
    
    # Build prompt components with explicit product visibility
    prompt_parts = [
        main_subject,
        style_info['style'],
        composition_emphasis if len(cleaned_names) > 1 else style_info['composition'],
        style_info['background'],
        style_info['lighting'],
        style_info['quality']
    ]
    
    # Join with natural flow
    prompt = ", ".join(prompt_parts)
    
    # Add category-specific enhancements with multi-product emphasis
    if len(products) > 1:
        # Always emphasize multiple products being shown together
        prompt += ", showing all items clearly"
        
        if context['primary_category'] == 'electronics' and context['tags'].intersection({'smartphone', 'phone'}):
            prompt += ", each device fully visible, premium materials"
        elif context['primary_category'] == 'food':
            prompt += ", appetizing presentation, each item distinct"
        elif context['is_mixed']:
            prompt += ", cohesive styling, each product prominently featured"
        else:
            prompt += ", balanced composition, no overlapping products"
    else:
        # Single product enhancements
        if context['primary_category'] == 'electronics' and context['tags'].intersection({'smartphone', 'phone'}):
            prompt += ", screen reflections, premium materials"
        elif context['primary_category'] == 'food':
            prompt += ", appetizing presentation"
    
    # Keep it under token limit with smart truncation
    return truncate_prompt_for_clip(prompt, max_tokens=55)  # Slightly higher for enhanced prompts


async def generate_bundle_image(bundle_name: str, products: List[ProductIn], description: Optional[str] = None) -> str:
    """
    Generate a single image for a bundle using local diffusers API.
    
    Args:
        bundle_name: Name of the bundle
        products: List of products in the bundle  
        description: Optional bundle description
        
    Returns:
        URL of the generated image
        
    Raises:
        ImageGenerationError: If image generation fails
    """
    # Check if mock mode is enabled (for testing without network calls)
    if is_mock_mode_enabled():
        logger.info(f"Mock mode enabled, generating mock image for bundle '{bundle_name}'")
        return generate_realistic_mock_image(bundle_name, products, description)
        
    if not products:
        raise ImageGenerationError("Cannot generate image for bundle with no products")
    
    try:
        # Build the prompt
        prompt = build_bundle_prompt(bundle_name, products, description)
        
        logger.info(f"Generating image for bundle '{bundle_name}' using local diffusers API")
        logger.info(f"Prompt: {prompt[:150]}...")
        
        # Call local image generation API with async support
        result = await call_local_image_api_async(prompt)
        
        if not result or not result.get("image_url"):
            raise ImageGenerationError(f"Local image API returned no image URL for bundle '{bundle_name}'")
        
        image_url = result["image_url"]
        method = result.get("method", "unknown")
        generation_time = result.get("generation_time", 0)
        
        # R2 upload is handled in the batch generation function
        # For single image generation, we'll use proxy URLs as fallback
        
        logger.info(f"Successfully generated image for bundle '{bundle_name}' via {method} in {generation_time:.2f}s: {image_url}")
        
        return image_url
        
    except ImageGenerationError:
        # Re-raise ImageGenerationErrors as-is
        raise
    except Exception as e:
        error_msg = f"Failed to generate image for bundle '{bundle_name}' using local API: {str(e)}"
        logger.error(error_msg)
        raise ImageGenerationError(error_msg) from e


# Synchronous wrapper for backward compatibility
def generate_bundle_image_sync(bundle_name: str, products: List[ProductIn], description: Optional[str] = None) -> str:
    """
    Synchronous wrapper for generate_bundle_image.
    """
    return asyncio.run(generate_bundle_image(bundle_name, products, description))


def generate_images_for_bundles(bundles: List[Bundle], max_concurrent: int = 3) -> Dict[int, Optional[str]]:
    """
    Generate images for multiple bundles using local diffusers API.
    
    Args:
        bundles: List of Bundle objects to generate images for
        max_concurrent: Maximum number of concurrent image generations
        
    Returns:
        Dictionary mapping bundle IDs to image URLs (or None if generation failed)
    """
    if not bundles:
        logger.warning("No bundles provided for image generation")
        return {}
    
    async def generate_single_bundle_image(bundle: Bundle) -> tuple[int, Optional[str]]:
        """Generate image for a single bundle (async)"""
        try:
            # Convert products JSONB to ProductIn objects
            products = []
            if isinstance(bundle.products, list):
                for product_data in bundle.products:
                    if isinstance(product_data, dict):
                        products.append(ProductIn(**product_data))
                    
            if not products:
                logger.warning(f"Bundle {bundle.id} has no valid products for image generation")
                return bundle.id, None
                
            # Generate image using async function
            image_url = await generate_bundle_image(
                bundle.name, 
                products, 
                bundle.description
            )
            
            # Upload to R2 if we got a local URL
            if image_url and (image_url.startswith("http://localhost:8001/images/") or image_url.startswith("https://image.huggle.tech/images/")):
                try:
                    from .r2_image_upload import upload_bundle_image
                    r2_url = upload_bundle_image(image_url, bundle.id)
                    
                    if r2_url and r2_url != image_url:  # R2 upload succeeded
                        logger.info(f"Bundle {bundle.id}: R2 upload successful: {r2_url}")
                        image_url = r2_url
                    else:
                        # Fallback to proxy URL
                        filename = image_url.split('/')[-1]
                        image_url = f"/api/images/generated/{filename}"
                        logger.info(f"Bundle {bundle.id}: Using proxy URL: {image_url}")
                        
                except Exception as e:
                    logger.error(f"Bundle {bundle.id}: R2 upload failed: {e}")
                    filename = image_url.split('/')[-1]
                    image_url = f"/api/images/generated/{filename}"
            
            return bundle.id, image_url
            
        except Exception as e:
            logger.error(f"Failed to generate image for bundle {bundle.id}: {str(e)}")
            return bundle.id, None
    
    async def generate_all_images():
        """Generate images for all bundles with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(bundle: Bundle):
            async with semaphore:
                return await generate_single_bundle_image(bundle)
        
        tasks = [generate_with_semaphore(bundle) for bundle in bundles]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    # Run the async image generation
    try:
        return asyncio.run(generate_all_images())
    except Exception as e:
        logger.error(f"Batch image generation failed: {str(e)}")
        return {}


def update_bundle_with_image(db: Session, bundle_id: int, image_url: str) -> bool:
    """
    Update a bundle with the generated image URL.
    
    Args:
        db: Database session
        bundle_id: ID of the bundle to update
        image_url: URL of the generated image
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
        if not bundle:
            logger.error(f"Bundle {bundle_id} not found for image update")
            return False
            
        bundle.image_url = image_url
        db.commit()
        
        logger.info(f"Updated bundle {bundle_id} with image URL: {image_url}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update bundle {bundle_id} with image URL: {str(e)}")
        return False


def generate_and_update_bundle_image(db: Session, bundle_id: int) -> Optional[str]:
    """
    Generate an image for a bundle and update the database record.
    
    Args:
        db: Database session
        bundle_id: ID of the bundle to generate image for
        
    Returns:
        Image URL if successful, None if failed
    """
    async def _async_generate_and_update():
        try:
            # Get the bundle
            bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
            if not bundle:
                raise ImageGenerationError(f"Bundle {bundle_id} not found")
                
            # Convert products to ProductIn objects
            products = []
            if isinstance(bundle.products, list):
                for product_data in bundle.products:
                    if isinstance(product_data, dict):
                        products.append(ProductIn(**product_data))
            
            if not products:
                raise ImageGenerationError(f"Bundle {bundle_id} has no valid products")
                
            # Generate the image
            image_url = await generate_bundle_image(bundle.name, products, bundle.description)
            
            # Update the bundle
            if update_bundle_with_image(db, bundle_id, image_url):
                return image_url
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate and update image for bundle {bundle_id}: {str(e)}")
            return None
    
    # Run the async function
    return asyncio.run(_async_generate_and_update())

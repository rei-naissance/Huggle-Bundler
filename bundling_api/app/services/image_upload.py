"""
Image Upload Service for Bundle Images

Handles uploading generated images to cloud storage (Cloudinary/S3) 
and returns publicly accessible URLs for frontend use.
"""

import os
import requests
import logging
import time
from typing import Optional
from pathlib import Path
import base64

logger = logging.getLogger(__name__)

# Configuration - Add these to your .env file
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY") 
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_UPLOAD_PRESET = os.getenv("CLOUDINARY_UPLOAD_PRESET", "bundle_images")


class ImageUploadError(Exception):
    """Custom exception for image upload failures"""
    pass


def upload_image_to_cloudinary(image_url: str, bundle_id: int) -> Optional[str]:
    """
    Upload image from local URL to Cloudinary and return public URL.
    
    Args:
        image_url: Local image URL (e.g., http://localhost:8001/images/abc.png)
        bundle_id: Bundle ID for naming/organization
        
    Returns:
        Public Cloudinary URL or None if upload fails
    """
    if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
        logger.warning("Cloudinary credentials not configured, skipping upload")
        return image_url  # Return original URL as fallback
    
    try:
        # Download image from local server
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Convert to base64 for Cloudinary upload
        image_data = base64.b64encode(response.content).decode('utf-8')
        data_uri = f"data:image/png;base64,{image_data}"
        
        # Upload to Cloudinary
        upload_url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
        
        upload_data = {
            "file": data_uri,
            "api_key": CLOUDINARY_API_KEY,
            "api_secret": CLOUDINARY_API_SECRET,
            "public_id": f"bundles/bundle_{bundle_id}_{int(time.time())}",
            "folder": "bundle_images",
            "tags": "bundle,ai_generated",
            "overwrite": True,
            "resource_type": "image"
        }
        
        upload_response = requests.post(upload_url, data=upload_data, timeout=60)
        upload_response.raise_for_status()
        
        result = upload_response.json()
        public_url = result.get("secure_url")
        
        if public_url:
            logger.info(f"Successfully uploaded bundle {bundle_id} image to Cloudinary: {public_url}")
            return public_url
        else:
            raise ImageUploadError("No secure_url in Cloudinary response")
            
    except requests.RequestException as e:
        logger.error(f"Failed to download or upload image for bundle {bundle_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading image for bundle {bundle_id}: {e}")
        return None


def upload_image_to_s3(image_url: str, bundle_id: int) -> Optional[str]:
    """
    Upload image to AWS S3 (alternative to Cloudinary).
    
    Requires: boto3, AWS credentials configured
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.warning("boto3 not installed, cannot upload to S3")
        return None
    
    # S3 configuration
    S3_BUCKET = os.getenv("S3_BUCKET_NAME")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    
    if not S3_BUCKET:
        logger.warning("S3 bucket not configured")
        return None
    
    try:
        # Download image from local server
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Upload to S3
        s3_client = boto3.client('s3', region_name=S3_REGION)
        key = f"bundle-images/bundle_{bundle_id}_{int(time.time())}.png"
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=response.content,
            ContentType='image/png',
            ACL='public-read'  # Make publicly accessible
        )
        
        # Generate public URL
        public_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
        
        logger.info(f"Successfully uploaded bundle {bundle_id} image to S3: {public_url}")
        return public_url
        
    except ClientError as e:
        logger.error(f"S3 upload failed for bundle {bundle_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3 for bundle {bundle_id}: {e}")
        return None


def upload_bundle_image(local_image_url: str, bundle_id: int) -> str:
    """
    Main function to upload bundle image to cloud storage.
    
    Tries Cloudinary first, falls back to S3, then returns original URL.
    
    Args:
        local_image_url: Local image URL from image generation server
        bundle_id: Bundle ID for organization
        
    Returns:
        Public cloud URL or original URL as fallback
    """
    # Try Cloudinary first
    cloudinary_url = upload_image_to_cloudinary(local_image_url, bundle_id)
    if cloudinary_url and not cloudinary_url.startswith("http://localhost"):
        return cloudinary_url
    
    # Try S3 as fallback
    s3_url = upload_image_to_s3(local_image_url, bundle_id)
    if s3_url:
        return s3_url
    
    # Return original URL as last resort
    logger.warning(f"All cloud uploads failed for bundle {bundle_id}, using local URL")
    return local_image_url


# Quick setup helper
def setup_cloudinary_env():
    """
    Print instructions for setting up Cloudinary environment variables.
    """
    print("🚀 To set up Cloudinary image uploads:")
    print("1. Sign up at https://cloudinary.com (free tier available)")
    print("2. Get your credentials from the dashboard")
    print("3. Add to your .env file:")
    print("")
    print("CLOUDINARY_CLOUD_NAME=your_cloud_name")
    print("CLOUDINARY_API_KEY=your_api_key")
    print("CLOUDINARY_API_SECRET=your_api_secret")
    print("")
    print("4. Restart your server")
    print("5. Images will automatically upload to Cloudinary! 🎉")


if __name__ == "__main__":
    setup_cloudinary_env()
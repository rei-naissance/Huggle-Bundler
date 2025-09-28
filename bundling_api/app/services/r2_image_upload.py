"""
CloudFlare R2 Image Upload Service

Uploads AI-generated images to CloudFlare R2 storage and returns public URLs.
Uses S3-compatible API for seamless integration.
"""

import os
import requests
import logging
import time
import uuid
from typing import Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try manual loading
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

logger = logging.getLogger(__name__)

def get_r2_config():
    """
    Get R2 configuration from environment variables.
    This ensures fresh loading each time to avoid import-time issues.
    """
    return {
        'bucket_name': os.getenv("R2_BUCKET_NAME"),
        'endpoint_url': os.getenv("R2_ENDPOINT_URL"),
        'access_key_id': os.getenv("R2_ACCESS_KEY_ID"),
        'secret_access_key': os.getenv("R2_SECRET_ACCESS_KEY"),
        'region': os.getenv("R2_REGION", "auto"),
        'public_domain': os.getenv("R2_PUBLIC_DOMAIN")
    }


class R2UploadError(Exception):
    """Custom exception for R2 upload failures"""
    pass


def get_r2_client():
    """
    Create and return S3-compatible client for CloudFlare R2.
    """
    config = get_r2_config()
    
    if not all([config['bucket_name'], config['endpoint_url'], config['access_key_id'], config['secret_access_key']]):
        raise R2UploadError("R2 credentials not configured. Check your .env file.")
    
    try:
        client = boto3.client(
            's3',
            endpoint_url=config['endpoint_url'],
            aws_access_key_id=config['access_key_id'],
            aws_secret_access_key=config['secret_access_key'],
            region_name=config['region']
        )
        return client
    except Exception as e:
        raise R2UploadError(f"Failed to create R2 client: {e}")


def upload_image_to_r2(local_image_url: str, bundle_id: int) -> Optional[str]:
    """
    Upload image from local server to CloudFlare R2 and return public URL.
    
    Args:
        local_image_url: Local image URL (e.g., http://localhost:8001/images/abc123.png)
        bundle_id: Bundle ID for organizing images
        
    Returns:
        Public R2 URL or None if upload fails
    """
    try:
        # Get R2 configuration at runtime
        config = get_r2_config()
        
        # Log configuration for debugging
        logger.info(f"R2 Configuration for bundle {bundle_id}:")
        logger.info(f"  BUCKET_NAME: {config['bucket_name']}")
        logger.info(f"  PUBLIC_DOMAIN: {config['public_domain']}")
        logger.info(f"  ENDPOINT_URL: {config['endpoint_url']}")
        
        # Download image from local server
        logger.info(f"Downloading image for bundle {bundle_id}: {local_image_url}")
        response = requests.get(local_image_url, timeout=30)
        response.raise_for_status()
        
        image_data = response.content
        file_size = len(image_data)
        
        # Generate unique filename
        original_filename = local_image_url.split('/')[-1]
        timestamp = int(time.time())
        unique_filename = f"bundle-{bundle_id}-{timestamp}-{original_filename}"
        
        # S3 key (path in bucket)
        s3_key = f"bundle-images/{unique_filename}"
        
        # Get R2 client
        r2_client = get_r2_client()
        
        # Upload to R2
        logger.info(f"Uploading {file_size} bytes to R2: {s3_key}")
        r2_client.put_object(
            Bucket=config['bucket_name'],
            Key=s3_key,
            Body=image_data,
            ContentType='image/png',
            ContentDisposition=f'inline; filename="{unique_filename}"',
            CacheControl='public, max-age=31536000',  # Cache for 1 year
            Metadata={
                'bundle_id': str(bundle_id),
                'original_filename': original_filename,
                'upload_timestamp': str(timestamp)
            }
        )
        
        # Generate public URL - ALWAYS use configured domain if available
        if config['public_domain']:
            # Use custom domain if configured
            public_url = f"{config['public_domain'].rstrip('/')}/{s3_key}"
            logger.info(f"✅ Using configured R2_PUBLIC_DOMAIN: {config['public_domain']}")
        else:
            # Use R2 public URL format: https://pub-<account_hash>.r2.dev/bucket-name/key
            # Extract account hash from endpoint URL
            account_hash = config['endpoint_url'].split('.')[0].split('//')[-1]
            public_url = f"https://pub-{account_hash}.r2.dev/{config['bucket_name']}/{s3_key}"
            logger.warning(f"❌ R2_PUBLIC_DOMAIN not configured, using fallback URL generation")
            logger.info(f"Generated fallback URL with account_hash: {account_hash}")
        
        logger.info(f"Successfully uploaded bundle {bundle_id} image to R2: {public_url}")
        logger.info(f"File size: {file_size} bytes, S3 key: {s3_key}")
        
        return public_url
        
    except requests.RequestException as e:
        logger.error(f"Failed to download image for bundle {bundle_id}: {e}")
        return None
    except ClientError as e:
        logger.error(f"R2 upload failed for bundle {bundle_id}: {e}")
        return None
    except R2UploadError as e:
        logger.error(f"R2 configuration error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading to R2 for bundle {bundle_id}: {e}")
        return None


def delete_image_from_r2(s3_key: str) -> bool:
    """
    Delete image from R2 storage.
    
    Args:
        s3_key: S3 key of the image to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        config = get_r2_config()
        r2_client = get_r2_client()
        r2_client.delete_object(Bucket=config['bucket_name'], Key=s3_key)
        logger.info(f"Deleted image from R2: {s3_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete image from R2: {s3_key}, error: {e}")
        return False


def list_r2_images(prefix: str = "bundle-images/", max_keys: int = 100):
    """
    List images in R2 bucket (for debugging/management).
    
    Args:
        prefix: S3 key prefix to filter by
        max_keys: Maximum number of objects to return
        
    Returns:
        List of S3 objects
    """
    try:
        config = get_r2_config()
        r2_client = get_r2_client()
        response = r2_client.list_objects_v2(
            Bucket=config['bucket_name'],
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = response.get('Contents', [])
        logger.info(f"Found {len(objects)} objects in R2 with prefix '{prefix}'")
        return objects
        
    except Exception as e:
        logger.error(f"Failed to list R2 objects: {e}")
        return []


def test_r2_connection():
    """
    Test R2 connection and permissions.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        config = get_r2_config()
        r2_client = get_r2_client()
        
        # Test by listing objects (this requires minimal permissions)
        response = r2_client.list_objects_v2(Bucket=config['bucket_name'], MaxKeys=1)
        
        logger.info(f"✅ R2 connection successful! Bucket: {config['bucket_name']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ R2 connection failed: {e}")
        return False


# Main upload function for integration
def upload_bundle_image(local_image_url: str, bundle_id: int) -> str:
    """
    Main function to upload bundle image to R2.
    
    Args:
        local_image_url: Local image URL from image generation server
        bundle_id: Bundle ID for organization
        
    Returns:
        Public R2 URL or fallback to original URL
    """
    try:
        # Upload to R2
        r2_url = upload_image_to_r2(local_image_url, bundle_id)
        
        if r2_url:
            return r2_url
        else:
            # Fallback to original URL
            logger.warning(f"R2 upload failed for bundle {bundle_id}, using original URL")
            return local_image_url
            
    except Exception as e:
        logger.error(f"Error in upload_bundle_image: {e}")
        return local_image_url


if __name__ == "__main__":
    print("🚀 CloudFlare R2 Image Upload Service")
    print("=" * 50)
    
    # Get configuration
    config = get_r2_config()
    
    # Test connection
    if test_r2_connection():
        print("✅ R2 connection successful!")
        
        # List current images
        images = list_r2_images()
        print(f"📁 Current images in bucket: {len(images)}")
        
        if images:
            print("\n🖼️ Recent images:")
            for img in images[:5]:  # Show first 5
                print(f"  - {img['Key']} ({img['Size']} bytes)")
    else:
        print("❌ R2 connection failed!")
        print("\n🔧 Check your .env configuration:")
        print(f"  R2_BUCKET_NAME: {config['bucket_name']}")
        print(f"  R2_ENDPOINT_URL: {config['endpoint_url']}")
        print(f"  R2_ACCESS_KEY_ID: {'✅' if config['access_key_id'] else '❌'}")
        print(f"  R2_SECRET_ACCESS_KEY: {'✅' if config['secret_access_key'] else '❌'}")
        print(f"  R2_PUBLIC_DOMAIN: {config['public_domain']}")

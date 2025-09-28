"""
Database Image Storage Service

Stores generated images directly in Neon PostgreSQL database as BYTEA
and serves them via API endpoints for frontend access.
"""

import requests
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, LargeBinary, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from fastapi import HTTPException
from fastapi.responses import Response

from ..db import Base, engine

logger = logging.getLogger(__name__)


class BundleImage(Base):
    """Model for storing bundle images in database"""
    __tablename__ = "bundle_images"
    
    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, index=True, nullable=False)
    image_data = Column(LargeBinary, nullable=False)  # Store image as binary data
    content_type = Column(String, default="image/png")
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


def download_and_store_image(local_image_url: str, bundle_id: int, db: Session) -> Optional[str]:
    """
    Download image from local server and store in database.
    
    Args:
        local_image_url: URL from image generation server (http://localhost:8001/images/abc.png)
        bundle_id: Bundle ID to associate with
        db: Database session
        
    Returns:
        Database image URL or None if failed
    """
    try:
        # Download image from local server
        logger.info(f"Downloading image for bundle {bundle_id}: {local_image_url}")
        response = requests.get(local_image_url, timeout=30)
        response.raise_for_status()
        
        # Extract filename from URL
        filename = local_image_url.split('/')[-1]
        if not filename.endswith('.png'):
            filename = f"{filename}.png"
        
        image_data = response.content
        file_size = len(image_data)
        
        # Store in database
        db_image = BundleImage(
            bundle_id=bundle_id,
            image_data=image_data,
            content_type="image/png",
            filename=filename,
            file_size=file_size
        )
        
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        
        # Return database URL that frontend can access
        database_url = f"/api/bundles/{bundle_id}/image"
        
        logger.info(f"Successfully stored image for bundle {bundle_id} in database (size: {file_size} bytes)")
        return database_url
        
    except requests.RequestException as e:
        logger.error(f"Failed to download image for bundle {bundle_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to store image for bundle {bundle_id} in database: {e}")
        db.rollback()
        return None


def get_bundle_image_from_db(bundle_id: int, db: Session) -> Optional[BundleImage]:
    """
    Retrieve bundle image from database.
    
    Args:
        bundle_id: Bundle ID
        db: Database session
        
    Returns:
        BundleImage object or None if not found
    """
    return db.query(BundleImage).filter(BundleImage.bundle_id == bundle_id).first()


def delete_bundle_image(bundle_id: int, db: Session) -> bool:
    """
    Delete bundle image from database.
    
    Args:
        bundle_id: Bundle ID
        db: Database session
        
    Returns:
        True if deleted, False if not found
    """
    try:
        db_image = db.query(BundleImage).filter(BundleImage.bundle_id == bundle_id).first()
        if db_image:
            db.delete(db_image)
            db.commit()
            logger.info(f"Deleted image for bundle {bundle_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete image for bundle {bundle_id}: {e}")
        db.rollback()
        return False


# Create tables
def create_image_tables():
    """Create image storage tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Bundle image tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create image tables: {e}")


if __name__ == "__main__":
    create_image_tables()
    print("✅ Database image storage tables created!")
    print("📋 Usage:")
    print("1. Images are automatically stored when bundles are created with images")
    print("2. Frontend accesses images via: /api/bundles/{bundle_id}/image") 
    print("3. No cloud storage needed - everything in your Neon database! 🎉")
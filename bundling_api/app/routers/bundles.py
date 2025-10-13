from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..db import get_db, engine
from ..schemas.bundle import BundleOut, BundleCreate, RecommendRequest, AIRecommendRequest
from ..repositories.bundles import create_bundle, get_bundle, list_bundles_by_store
from ..services.recommender import recommend_bundles
from ..services.ai import generate_bundles_for_store
from ..services.image_generator import (
    generate_and_update_bundle_image, 
    generate_images_for_bundles, 
    ImageGenerationError
)
from ..models.bundle import Bundle

router = APIRouter()


@router.post("/recommend", response_model=List[BundleCreate])
def recommend(req: RecommendRequest, db: Session = Depends(get_db)):
    bundles = recommend_bundles(db, store_id=req.store_id, num_bundles=req.num_bundles)
    return bundles


@router.post("/recommend/ai", response_model=List[BundleCreate])
def recommend_ai(req: AIRecommendRequest, db: Session = Depends(get_db)):
    bundles = generate_bundles_for_store(db, store_id=req.store_id, num_bundles=req.num_bundles)
    return bundles


@router.post("/recommend/ai/save", response_model=List[BundleOut])
def recommend_ai_and_save(req: AIRecommendRequest, db: Session = Depends(get_db)):
    candidates = generate_bundles_for_store(db, store_id=req.store_id, num_bundles=req.num_bundles)
    saved_out: list[BundleOut] = []
    for c in candidates:
        saved = create_bundle(db, c)
        saved_out.append(
            BundleOut(
                id=saved.id,
                name=saved.name,
                description=saved.description,
                products=saved.products,
                images=saved.images,
                image_url=saved.image_url,
                stock=saved.stock,
                price=float(saved.price) if saved.price else None,
                original_price=float(saved.original_price) if saved.original_price else None,
                total_cost=float(saved.total_cost) if saved.total_cost else None,
                created_at=saved.created_at,
            )
        )
    return saved_out


@router.post("/save", response_model=BundleOut)
def save_bundle(bundle: BundleCreate, db: Session = Depends(get_db)):
    saved = create_bundle(db, bundle)
    # Return as BundleOut
    return BundleOut(
        id=saved.id,
        name=saved.name,
        description=saved.description,
        products=saved.products,  # pydantic will coerce list of dicts
        images=saved.images,
        image_url=saved.image_url,
        stock=saved.stock,
        price=float(saved.price) if saved.price else None,
        original_price=float(saved.original_price) if saved.original_price else None,
        total_cost=float(saved.total_cost) if saved.total_cost else None,
        created_at=saved.created_at,
    )


@router.get("/{bundle_id}", response_model=BundleOut)
def get_bundle_by_id(bundle_id: str, db: Session = Depends(get_db)):
    b = get_bundle(db, bundle_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return BundleOut(
        id=b.id,
        name=b.name,
        description=b.description,
        products=b.products,
        images=b.images,
        image_url=b.image_url,
        stock=b.stock,
        price=float(b.price) if b.price else None,
        original_price=float(b.original_price) if b.original_price else None,
        total_cost=float(b.total_cost) if b.total_cost else None,
        created_at=b.created_at,
    )


@router.get("", response_model=List[BundleOut])
def list_bundles(store_id: str = Query(...), limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    items = list_bundles_by_store(db, store_id=store_id, limit=limit, offset=offset)
    return [
        BundleOut(
            id=b.id,
            name=b.name,
            description=b.description,
            products=b.products,
            images=b.images,
            image_url=b.image_url,
            stock=b.stock,
            price=float(b.price) if b.price else None,
            original_price=float(b.original_price) if b.original_price else None,
            total_cost=float(b.total_cost) if b.total_cost else None,
            created_at=b.created_at,
        )
        for b in items
    ]


# IMAGE GENERATION ENDPOINTS

@router.post("/{bundle_id}/generate-image")
def generate_image_for_bundle(bundle_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Generate an AI image for a specific bundle using Fal.AI.
    Updates the bundle record with the generated image URL.
    """
    try:
        image_url = generate_and_update_bundle_image(db, bundle_id)
        
        if image_url:
            return {
                "success": True,
                "bundle_id": bundle_id,
                "image_url": image_url,
                "message": f"Successfully generated image for bundle {bundle_id}"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate image for bundle {bundle_id}"
            )
            
    except ImageGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/generate-images/batch")
def generate_images_for_store_bundles(
    store_id: str,
    limit: int = Query(default=10, description="Maximum number of bundles to process"),
    max_concurrent: int = Query(default=3, description="Maximum concurrent image generations"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate AI images for multiple bundles in a store using Fal.AI.
    Processes bundles that don't already have images.
    """
    try:
        # Get bundles without images
        bundles_without_images = db.query(Bundle).filter(
            Bundle.store_id == store_id,
            Bundle.image_url.is_(None)
        ).limit(limit).all()
        
        if not bundles_without_images:
            return {
                "success": True,
                "processed": 0,
                "message": "No bundles found that need image generation"
            }
        
        # Generate images
        results = generate_images_for_bundles(bundles_without_images, max_concurrent)
        
        # Update bundles with generated images
        updated_count = 0
        failed_count = 0
        
        for bundle_id, image_url in results.items():
            if image_url:
                bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
                if bundle:
                    bundle.image_url = image_url
                    updated_count += 1
            else:
                failed_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "processed": len(bundles_without_images),
            "updated": updated_count,
            "failed": failed_count,
            "results": results,
            "message": f"Processed {len(bundles_without_images)} bundles, updated {updated_count}, failed {failed_count}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch image generation failed: {str(e)}")


@router.post("/recommend/ai/save-with-images", response_model=List[BundleOut])
def recommend_ai_save_and_generate_images(
    req: AIRecommendRequest, 
    db: Session = Depends(get_db)
) -> List[BundleOut]:
    """
    AI recommend bundles, save them, and immediately generate images.
    This combines bundle creation and image generation in one efficient call.
    """
    # Generate bundle recommendations
    candidates = generate_bundles_for_store(db, store_id=req.store_id, num_bundles=req.num_bundles)
    
    if not candidates:
        return []
    
    saved_bundles = []
    
    # Save bundles first
    for candidate in candidates:
        saved = create_bundle(db, candidate)
        saved_bundles.append(saved)
    
    # Generate images for the saved bundles
    if saved_bundles:
        image_results = generate_images_for_bundles(saved_bundles, max_concurrent=3)
        
        # Update bundles with generated images (now frontend-accessible URLs)
        for bundle in saved_bundles:
            if bundle.id in image_results and image_results[bundle.id]:
                # Image URLs are already converted to public format in image_generator.py
                bundle.image_url = image_results[bundle.id]
        
        db.commit()
    
    # Convert to BundleOut format
    return [
        BundleOut(
            id=bundle.id,
            name=bundle.name,
            description=bundle.description,
            products=bundle.products,
            images=bundle.images,
            image_url=bundle.image_url,
            stock=bundle.stock,
            price=float(bundle.price) if bundle.price else None,
            original_price=float(bundle.original_price) if bundle.original_price else None,
            total_cost=float(bundle.total_cost) if bundle.total_cost else None,
            created_at=bundle.created_at,
        )
        for bundle in saved_bundles
    ]

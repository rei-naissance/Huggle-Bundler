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
from ..config import settings

router = APIRouter()


@router.post("/debug-ai-config")
def debug_ai_configuration(
    req: AIRecommendRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Temporary debug endpoint to check AI configuration and store data.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from ..clients.inventory import fetch_products_for_store
    from ..repositories.bundles import bundle_exists_for_products
    
    # Check AI configuration
    ai_config = {
        "ai_provider": settings.ai_provider,
        "openrouter_api_key_set": bool(settings.openrouter_api_key),
        "openrouter_model": settings.openrouter_model,
        "groq_api_key_set": bool(settings.groq_api_key),
        "groq_model": settings.groq_model,
    }
    
    # Check store products
    products_raw = fetch_products_for_store(db, req.store_id)
    
    # Check existing bundles
    existing_bundles = db.query(Bundle).filter(Bundle.store_id == req.store_id).all()
    
    # Sample bundle existence checks
    sample_checks = []
    if len(products_raw) >= 2:
        product_ids = [str(p.get("id")) for p in products_raw[:2]]
        exists = bundle_exists_for_products(db, req.store_id, product_ids)
        sample_checks.append({
            "product_ids": product_ids,
            "bundle_exists": exists
        })
    
    return {
        "store_id": req.store_id,
        "ai_config": ai_config,
        "products_count": len(products_raw),
        "products_sample": products_raw[:3] if products_raw else [],
        "existing_bundles_count": len(existing_bundles),
        "existing_bundles": [{
            "id": b.id,
            "name": b.name,
            "signature": b.signature
        } for b in existing_bundles],
        "sample_bundle_checks": sample_checks
    }


@router.post("/test-manual-bundle")
def test_manual_bundle_creation(
    req: AIRecommendRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Temporary test endpoint to create a bundle manually without AI.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from ..clients.inventory import fetch_products_for_store
    from ..schemas.bundle import ProductIn
    
    logger.info(f"🚀 Manual bundle test for store: {req.store_id}")
    
    # Fetch products
    products_raw = fetch_products_for_store(db, req.store_id)
    logger.info(f"Found {len(products_raw)} products")
    
    if len(products_raw) < 2:
        return {
            "success": False,
            "error": "Need at least 2 products to create a bundle",
            "products_count": len(products_raw)
        }
    
    # Take first 2 products and create a manual bundle
    p1, p2 = products_raw[0], products_raw[1]
    
    # Create ProductIn objects
    from ..utils.dates import parse_expiry as _safe_parse_dt
    from ..utils.text import parse_tags_str as __parse_tags
    from datetime import datetime, timezone
    
    def make_product_in(p):
        expires_on = _safe_parse_dt(p.get("expiresOn"))
        if expires_on is None or (isinstance(expires_on, datetime) and expires_on.year < 1900):
            expires_on = datetime(9999, 1, 1, tzinfo=timezone.utc)
        return ProductIn(
            id=str(p.get("id")),
            name=p.get("name") or "Unnamed",
            product_type=p.get("productType") or None,
            expires_on=expires_on,
            stock=int(p.get("stock") or 0),
            tags=__parse_tags(p.get("tags")),
            price=float(p.get("price") or 0.0),
            original_price=float(p.get("originalPrice") or 0.0),
        )
    
    product_in_1 = make_product_in(p1)
    product_in_2 = make_product_in(p2)
    
    # Create bundle
    from ..schemas.bundle import BundleCreate
    
    test_bundle = BundleCreate(
        store_id=req.store_id,
        name=f"Test Bundle: {product_in_1.name} + {product_in_2.name}",
        description=f"Manual test bundle with {product_in_1.name} and {product_in_2.name}",
        products=[product_in_1, product_in_2],
        images=[],
        stock=min(product_in_1.stock, product_in_2.stock)
    )
    
    try:
        # Try to create the bundle
        saved_bundle = create_bundle(db, test_bundle)
        
        return {
            "success": True,
            "bundle": BundleOut(
                id=saved_bundle.id,
                name=saved_bundle.name,
                description=saved_bundle.description,
                products=saved_bundle.products,
                images=saved_bundle.images,
                image_url=saved_bundle.image_url,
                stock=saved_bundle.stock,
                price=float(saved_bundle.price) if saved_bundle.price else None,
                original_price=float(saved_bundle.original_price) if saved_bundle.original_price else None,
                total_cost=float(saved_bundle.total_cost) if saved_bundle.total_cost else None,
                created_at=saved_bundle.created_at,
            ),
            "message": "Manual bundle created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create manual bundle: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "bundle_data": {
                "name": test_bundle.name,
                "products": [product_in_1.name, product_in_2.name]
            }
        }


@router.post("/test-ai-providers")
def test_ai_providers(
    req: AIRecommendRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Temporary test endpoint to test AI providers directly.
    """
    import httpx
    import logging
    logger = logging.getLogger(__name__)
    
    results = {
        "store_id": req.store_id,
        "groq_test": {},
        "openrouter_test": {}
    }
    
    # Test Groq
    if settings.groq_api_key and settings.groq_model:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Respond with valid JSON only."},
                    {"role": "user", "content": "Create a simple test response: {\"test\": \"success\", \"message\": \"Groq is working\"}"}
                ],
                "temperature": 0.1,
            }
            
            resp = httpx.post(url, headers=headers, json=data, timeout=httpx.Timeout(10.0))
            resp.raise_for_status()
            response_json = resp.json()
            
            results["groq_test"] = {
                "success": True,
                "status_code": resp.status_code,
                "model_used": settings.groq_model,
                "response_content": response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            }
        except Exception as e:
            results["groq_test"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "model_attempted": settings.groq_model
            }
    else:
        results["groq_test"] = {
            "success": False,
            "error": "API key or model not configured",
            "api_key_set": bool(settings.groq_api_key),
            "model_set": bool(settings.groq_model)
        }
    
    # Test OpenRouter
    if settings.openrouter_api_key:
        try:
            model = settings.openrouter_model or "openai/gpt-3.5-turbo"
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://huggle.tech",
                "X-Title": "Bundling API",
            }
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Respond with valid JSON only."},
                    {"role": "user", "content": "Create a simple test response: {\"test\": \"success\", \"message\": \"OpenRouter is working\"}"}
                ],
                "temperature": 0.1,
            }
            
            resp = httpx.post(url, headers=headers, json=data, timeout=httpx.Timeout(10.0))
            resp.raise_for_status()
            response_json = resp.json()
            
            results["openrouter_test"] = {
                "success": True,
                "status_code": resp.status_code,
                "model_used": model,
                "response_content": response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            }
        except Exception as e:
            results["openrouter_test"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "model_attempted": settings.openrouter_model
            }
    else:
        results["openrouter_test"] = {
            "success": False,
            "error": "API key not configured",
            "api_key_set": bool(settings.openrouter_api_key)
        }
    
    return results


@router.post("/debug-ai-verbose")
def debug_ai_verbose_test(
    req: AIRecommendRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verbose debug endpoint that calls generate_bundles_for_store with detailed output.
    """
    import logging
    import io
    import sys
    from contextlib import redirect_stderr, redirect_stdout
    
    # Capture all logging output
    log_capture = io.StringIO()
    log_handler = logging.StreamHandler(log_capture)
    log_handler.setLevel(logging.DEBUG)
    
    # Get the AI service logger
    ai_logger = logging.getLogger('app.services.ai')
    ai_logger.addHandler(log_handler)
    ai_logger.setLevel(logging.DEBUG)
    
    # Also get inventory logger
    inventory_logger = logging.getLogger('app.clients.inventory')
    inventory_logger.addHandler(log_handler)
    inventory_logger.setLevel(logging.DEBUG)
    
    try:
        # Call the actual function
        candidates = generate_bundles_for_store(db, store_id=req.store_id, num_bundles=req.num_bundles)
        
        # Get all log output
        log_output = log_capture.getvalue()
        
        return {
            "success": True,
            "store_id": req.store_id,
            "candidates_count": len(candidates),
            "candidates": [{
                "name": c.name,
                "product_count": len(c.products),
                "product_names": [p.name for p in c.products]
            } for c in candidates],
            "debug_logs": log_output.split('\n')[-50:],  # Last 50 log lines
            "full_log_length": len(log_output.split('\n'))
        }
    except Exception as e:
        log_output = log_capture.getvalue()
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "debug_logs": log_output.split('\n')[-50:],
            "full_log_length": len(log_output.split('\n'))
        }
    finally:
        # Clean up handlers
        ai_logger.removeHandler(log_handler)
        inventory_logger.removeHandler(log_handler)
        log_handler.close()


@router.post("/debug-combinations")
def debug_all_combinations(
    req: AIRecommendRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Debug endpoint to check all possible 2-product combinations for a store.
    """
    from itertools import combinations
    from ..clients.inventory import fetch_products_for_store
    from ..repositories.bundles import bundle_exists_for_products
    
    # Get all products
    products_raw = fetch_products_for_store(db, req.store_id)
    
    if len(products_raw) < 2:
        return {"error": "Need at least 2 products", "products_count": len(products_raw)}
    
    # Get all product IDs
    product_ids = [str(p.get("id")) for p in products_raw]
    product_names = {str(p.get("id")): p.get("name") for p in products_raw}
    
    # Test all 2-product combinations
    results = []
    for combo in combinations(product_ids, 2):
        combo_list = list(combo)
        exists = bundle_exists_for_products(db, req.store_id, combo_list)
        
        results.append({
            "product_ids": combo_list,
            "product_names": [product_names[pid] for pid in combo_list],
            "exists": exists
        })
    
    # Test all 3-product combinations
    results_3 = []
    for combo in combinations(product_ids, 3):
        combo_list = list(combo)
        exists = bundle_exists_for_products(db, req.store_id, combo_list)
        
        results_3.append({
            "product_ids": combo_list,
            "product_names": [product_names[pid] for pid in combo_list],
            "exists": exists
        })
    
    existing_count_2 = sum(1 for r in results if r["exists"])
    available_count_2 = sum(1 for r in results if not r["exists"])
    
    existing_count_3 = sum(1 for r in results_3 if r["exists"])
    available_count_3 = sum(1 for r in results_3 if not r["exists"])
    
    return {
        "store_id": req.store_id,
        "total_products": len(products_raw),
        "product_list": [{"id": pid, "name": product_names[pid]} for pid in product_ids],
        "two_product_combinations": {
            "total_possible": len(results),
            "existing": existing_count_2,
            "available": available_count_2,
            "details": results
        },
        "three_product_combinations": {
            "total_possible": len(results_3),
            "existing": existing_count_3, 
            "available": available_count_3,
            "sample_available": [r for r in results_3 if not r["exists"]][:3]
        }
        }


@router.post("/analyze-bundle-availability")
def analyze_bundle_availability(
    req: AIRecommendRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Comprehensive analysis of bundle availability for a store.
    Shows all possible combinations and which exist.
    """
    from itertools import combinations as combo_func
    from ..clients.inventory import fetch_products_for_store
    from ..repositories.bundles import bundle_exists_for_products, count_bundles_by_store
    
    # Get all products
    products_raw = fetch_products_for_store(db, req.store_id)
    
    if len(products_raw) < 2:
        return {"error": "Need at least 2 products", "products_count": len(products_raw)}
    
    # Get all product IDs and names
    product_ids = [str(p.get("id")) for p in products_raw]
    product_names = {str(p.get("id")): p.get("name") for p in products_raw}
    
    # Analyze all combination sizes
    analysis = {
        "store_id": req.store_id,
        "total_products": len(products_raw),
        "total_existing_bundles": count_bundles_by_store(db, req.store_id),
        "products": [{"id": pid, "name": product_names[pid]} for pid in product_ids],
        "combinations": {}
    }
    
    # Check combinations from size 2 to 5
    for size in range(2, min(6, len(products_raw) + 1)):
        combos = list(combo_func(product_ids, size))
        existing_count = 0
        available_combos = []
        
        for combo in combos:
            combo_list = list(combo)
            exists = bundle_exists_for_products(db, req.store_id, combo_list)
            
            if exists:
                existing_count += 1
            else:
                available_combos.append({
                    "product_ids": combo_list,
                    "product_names": [product_names[pid] for pid in combo_list]
                })
        
        analysis["combinations"][f"{size}_products"] = {
            "total_possible": len(combos),
            "existing": existing_count,
            "available": len(available_combos),
            "available_combinations": available_combos[:10]  # Show first 10
        }
    
    return analysis


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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 AI recommendation request received - Store ID: {req.store_id}, Num bundles: {req.num_bundles}")
    
    # Generate bundle recommendations
    logger.info(f"📦 Calling generate_bundles_for_store with store_id='{req.store_id}', num_bundles={req.num_bundles}")
    candidates = generate_bundles_for_store(db, store_id=req.store_id, num_bundles=req.num_bundles)
    logger.info(f"📊 Generated {len(candidates)} bundle candidates: {[c.name for c in candidates] if candidates else 'None'}")
    
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


@router.post("/recommend/ai/preview-with-images", response_model=List[BundleCreate])
def recommend_ai_preview_with_images(
    req: AIRecommendRequest, 
    db: Session = Depends(get_db)
) -> List[BundleCreate]:
    """
    AI recommend bundles and generate images WITHOUT saving to database.
    Returns bundle previews for user selection. User can then save selected
    bundle via the main backend's bundle creation endpoint.
    
    This is the recommended flow for UIs that show multiple bundle options
    and let the user select one to save.
    """
    import logging
    import uuid
    from datetime import datetime, timezone
    
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 AI preview request received - Store ID: {req.store_id}, Num bundles: {req.num_bundles}")
    
    # Generate bundle recommendations (BundleCreate schemas, not saved)
    logger.info(f"📦 Calling generate_bundles_for_store for preview with store_id='{req.store_id}', num_bundles={req.num_bundles}")
    candidates = generate_bundles_for_store(db, store_id=req.store_id, num_bundles=req.num_bundles)
    logger.info(f"📊 Generated {len(candidates)} preview candidates: {[c.name for c in candidates] if candidates else 'None'}")
    
    if not candidates:
        return []
    
    # Create temporary Bundle objects for image generation
    # These are NOT saved to the database
    temp_bundles = []
    candidate_to_temp_id = {}  # Map candidate index to temp bundle ID
    
    for i, candidate in enumerate(candidates):
        temp_id = str(uuid.uuid4())
        candidate_to_temp_id[i] = temp_id
        
        # Create a Bundle-like object for image generation
        # Using the actual Bundle model temporarily (won't be persisted)
        temp_bundle = Bundle(
            id=temp_id,
            store_id=candidate.store_id,
            name=candidate.name,
            description=candidate.description,
            products=[p.model_dump() for p in candidate.products],
            images=candidate.images or [],
            image_url=None,
            stock=candidate.stock,
            signature="preview",  # Marker for preview bundles
            price=candidate.price or 0,
            original_price=candidate.original_price or 0,
            total_cost=candidate.total_cost or 0,
            is_dynamic_pricing_enabled=False,
            dynamic_pricing_start_days=14,
            last_price_update=None,
            is_active=True,
            is_suspended=False,
            expires_on=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_on=None,
        )
        temp_bundles.append(temp_bundle)
    
    # Generate images for the temporary bundles (uploads to R2)
    logger.info(f"🎨 Generating images for {len(temp_bundles)} preview bundles...")
    image_results = generate_images_for_bundles(temp_bundles, max_concurrent=3)
    logger.info(f"📷 Image generation results: {len([v for v in image_results.values() if v])} successful")
    
    # Update candidates with generated image URLs
    for i, candidate in enumerate(candidates):
        temp_id = candidate_to_temp_id[i]
        if temp_id in image_results and image_results[temp_id]:
            candidate.image_url = image_results[temp_id]
            logger.info(f"✅ Preview bundle '{candidate.name}' got image: {candidate.image_url}")
    
    logger.info(f"✨ Returning {len(candidates)} preview bundles (not saved to database)")
    return candidates

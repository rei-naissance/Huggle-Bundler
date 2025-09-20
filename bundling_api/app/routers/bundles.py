from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.orm import Session

from ..db import get_db, engine
from ..schemas.bundle import BundleOut, BundleCreate, RecommendRequest, AIRecommendRequest
from ..repositories.bundles import create_bundle, get_bundle, list_bundles_by_seller
from ..services.recommender import recommend_bundles
from ..services.ai import generate_bundles_from_inventory
from ..clients.inventory import ensure_store_id_for_bundle

router = APIRouter()


@router.post("/recommend", response_model=List[BundleCreate])
def recommend(req: RecommendRequest, db: Session = Depends(get_db)):
    bundles = recommend_bundles(db, seller_id=req.seller_id, num_bundles=req.num_bundles)
    return bundles


@router.post("/recommend/ai", response_model=List[BundleCreate])
def recommend_ai(req: AIRecommendRequest, db: Session = Depends(get_db)):
    bundles = generate_bundles_from_inventory(db, seller_id=req.seller_id, num_bundles=req.num_bundles)
    return bundles


@router.post("/recommend/ai/save", response_model=List[BundleOut])
def recommend_ai_and_save(req: AIRecommendRequest, db: Session = Depends(get_db)):
    candidates = generate_bundles_from_inventory(db, seller_id=req.seller_id, num_bundles=req.num_bundles)
    saved_out: list[BundleOut] = []
    for c in candidates:
        c = ensure_store_id_for_bundle(db, c)
        saved = create_bundle(db, c)
        saved_out.append(
            BundleOut(
                id=saved.id,
                name=saved.name,
                description=saved.description,
                products=saved.products,
                images=saved.images,
                stock=saved.stock,
                created_at=saved.created_at,
            )
        )
    return saved_out


@router.post("/save", response_model=BundleOut)
def save_bundle(bundle: BundleCreate, db: Session = Depends(get_db)):
    # Ensure store_id if not provided
    bundle = ensure_store_id_for_bundle(db, bundle)
    saved = create_bundle(db, bundle)
    # Return as BundleOut
    return BundleOut(
        id=saved.id,
        name=saved.name,
        description=saved.description,
        products=saved.products,  # pydantic will coerce list of dicts
        images=saved.images,
        stock=saved.stock,
        created_at=saved.created_at,
    )


@router.get("/{bundle_id}", response_model=BundleOut)
def get_bundle_by_id(bundle_id: int, db: Session = Depends(get_db)):
    b = get_bundle(db, bundle_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return BundleOut(
        id=b.id,
        name=b.name,
        description=b.description,
        products=b.products,
        images=b.images,
        stock=b.stock,
        created_at=b.created_at,
    )


@router.get("", response_model=List[BundleOut])
def list_bundles(seller_id: str = Query(...), limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    items = list_bundles_by_seller(db, seller_id=seller_id, limit=limit, offset=offset)
    return [
        BundleOut(
            id=b.id,
            name=b.name,
            description=b.description,
            products=b.products,
            images=b.images,
            stock=b.stock,
            created_at=b.created_at,
        )
        for b in items
    ]

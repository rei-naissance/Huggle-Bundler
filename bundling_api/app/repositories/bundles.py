from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.bundle import Bundle
from ..schemas.bundle import BundleCreate


def create_bundle(db: Session, data: BundleCreate) -> Bundle:
    bundle = Bundle(
        seller_id=data.seller_id,
        store_id=data.store_id or "",
        name=data.name,
        description=data.description,
        products=[p.model_dump(mode="json") for p in data.products],
        images=data.images or [],
        stock=data.stock,
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return bundle


def get_bundle(db: Session, bundle_id: int) -> Optional[Bundle]:
    return db.query(Bundle).filter(Bundle.id == bundle_id).first()


def list_bundles_by_seller(db: Session, seller_id: str, limit: int = 50, offset: int = 0) -> List[Bundle]:
    return (
        db.query(Bundle)
        .filter(Bundle.seller_id == seller_id)
        .order_by(Bundle.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

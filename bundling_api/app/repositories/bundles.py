from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import uuid

from ..models.bundle import Bundle
from ..schemas.bundle import BundleCreate
from ..utils.signatures import compute_bundle_signature


def create_bundle(db: Session, data: BundleCreate) -> Bundle:
    """Create a new bundle with automatic signature computation.
    
    Raises:
        ValueError: If a bundle with the same products already exists in this store
        ValueError: If no valid products are provided for signature computation
    """
    products_data = [p.model_dump(mode="json") for p in data.products]
    
    # Compute signature for deduplication
    try:
        signature = compute_bundle_signature(products_data)
    except ValueError as e:
        raise ValueError(f"Cannot create bundle: {str(e)}")
    
    bundle = Bundle(
        id=str(uuid.uuid4()),
        store_id=data.store_id or "",
        signature=signature,
        name=data.name,
        description=data.description,
        products=products_data,
        images=data.images or [],
        stock=data.stock,
    )
    
    try:
        db.add(bundle)
        db.commit()
        db.refresh(bundle)
        return bundle
    except IntegrityError as e:
        db.rollback()
        # Check if this is a duplicate bundle error
        if 'uq_bundle_store_signature' in str(e.orig):
            raise ValueError(
                f"A bundle with the same products already exists in store {data.store_id}"
            )
        # Re-raise other integrity errors
        raise


def get_bundle(db: Session, bundle_id: str) -> Optional[Bundle]:
    return db.query(Bundle).filter(Bundle.id == bundle_id).first()


def list_bundles_by_store(db: Session, store_id: str, limit: int = 50, offset: int = 0) -> List[Bundle]:
    return (
        db.query(Bundle)
        .filter(Bundle.store_id == store_id)
        .order_by(Bundle.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def bundle_exists_for_products(db: Session, store_id: str, product_ids: List[str]) -> bool:
    """Check if a bundle already exists for the given product IDs in a store.
    
    Args:
        db: Database session
        store_id: The store ID to check within
        product_ids: List of product ID strings
        
    Returns:
        True if a bundle with the same product set exists, False otherwise
    """
    try:
        from ..utils.signatures import compute_signature_from_id_list
        signature = compute_signature_from_id_list(product_ids)
        
        existing = db.query(Bundle).filter(
            Bundle.store_id == store_id,
            Bundle.signature == signature
        ).first()
        
        return existing is not None
    except ValueError:
        # Invalid product IDs, bundle doesn't exist
        return False


def count_bundles_by_store(db: Session, store_id: str) -> int:
    """Count the total number of bundles for a store."""
    return db.query(Bundle).filter(Bundle.store_id == store_id).count()

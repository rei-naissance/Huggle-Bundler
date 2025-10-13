from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import uuid
import logging
from datetime import datetime, timedelta

from ..models.bundle import Bundle
from ..schemas.bundle import BundleCreate
from ..utils.signatures import compute_bundle_signature
from ..services.pricing import calculate_bundle_pricing

logger = logging.getLogger(__name__)


def create_bundle(db: Session, data: BundleCreate) -> Bundle:
    """Create a new bundle with automatic signature computation and pricing calculation.
    
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
    
    # Calculate pricing information
    pricing_info = {}
    try:
        if data.products:  # Only calculate if we have products with pricing
            raw_pricing = calculate_bundle_pricing(data.products)
            logger.info(f"Calculated pricing for bundle: {raw_pricing}")
            
            # Map to database field names
            pricing_info = {
                'original_price': raw_pricing.get('total_price', 0.0),  # Sum of individual prices
                'price': raw_pricing.get('discounted_price', raw_pricing.get('total_price', 0.0)),  # Final selling price
                'total_cost': raw_pricing.get('total_price', 0.0),  # Cost calculation (same as total for now)
            }
    except Exception as e:
        logger.warning(f"Failed to calculate pricing for bundle: {e}")
        # Set default pricing values if calculation fails
        total_price = sum(p.price for p in data.products) if data.products else 0.0
        pricing_info = {
            'original_price': total_price,
            'price': total_price,
            'total_cost': total_price,
        }
    
    bundle = Bundle(
        id=str(uuid.uuid4()),
        store_id=data.store_id or "",
        signature=signature,
        name=data.name,
        description=data.description,
        products=products_data,
        images=data.images or [],
        stock=data.stock,
        # Add pricing fields using correct database column names
        price=pricing_info.get('price', 0.0),
        original_price=pricing_info.get('original_price', 0.0),
        total_cost=pricing_info.get('total_cost', 0.0),
        is_dynamic_pricing_enabled=False,
        dynamic_pricing_start_days=14,
        is_active=True,
        expires_on=datetime.utcnow() + timedelta(days=30),
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

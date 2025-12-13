from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException


def fetch_products_for_store(db: Session, store_id: str) -> List[Dict]:
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🛒 fetch_products_for_store called with store_id: '{store_id}'")
    
    # Dynamically detect presence of products.is_suspended (snake_case)
    has_is_suspended = False
    try:
        col_check = db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'is_suspended'
                LIMIT 1
                """
            )
        ).first()
        has_is_suspended = col_check is not None
    except Exception:
        # If information_schema is unavailable for any reason, assume column may not exist
        has_is_suspended = False

    select_fields = (
        "id, name, \"productType\", \"expiresOn\", stock, tags, price, \"originalPrice\", \"productCost\""
        + (", is_suspended" if has_is_suspended else "")
    )
    where_clause = "\"storeId\" = :store_id AND (\"isActive\" = true OR \"isActive\" IS NULL)"
    if has_is_suspended:
        # Exclude suspended products for bundle generation
        where_clause += " AND COALESCE(is_suspended, false) = false"

    q = text(
        f"""
        SELECT {select_fields}
        FROM products
        WHERE {where_clause}
        """
    )
    try:
        logger.debug(f"📄 Executing query for store_id: {store_id}")
        res = db.execute(q, {"store_id": store_id})
        logger.debug("✅ Query executed successfully")
    except OperationalError as e:
        logger.error(f"💥 Database operation failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    out: List[Dict] = []
    row_count = 0
    for row in res.mappings():
        out.append(dict(row))
        row_count += 1
        if row_count <= 3:  # Log first 3 products for debugging
            logger.debug(f"Sample product {row_count}: {dict(row)['name']} (ID: {dict(row)['id']})")
    if has_is_suspended:
        # Double-check none are suspended if caller runs without WHERE due to fallback
        filtered_count = sum(1 for p in out if bool(p.get("is_suspended")))
        if filtered_count:
            logger.warning(f"⚠️ Retrieved {filtered_count} suspended products unexpectedly; they will be ignored upstream")
    
    logger.info(f"🎯 fetch_products_for_store returning {len(out)} products for store '{store_id}'")
    return out

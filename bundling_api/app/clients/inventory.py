from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..schemas.bundle import BundleCreate


def get_store_id_for_seller(db: Session, seller_id: str) -> str | None:
    # stores has unique index on sellerId
    q = text("SELECT id FROM stores WHERE \"sellerId\" = :sid LIMIT 1")
    row = db.execute(q, {"sid": seller_id}).fetchone()
    return row[0] if row else None


def fetch_products_for_store(db: Session, store_id: str) -> List[Dict]:
    # Fetch minimal fields needed for recommendations
    q = text(
        """
        SELECT id, name, "productType", "expiresOn", stock, tags
        FROM products
        WHERE "storeId" = :store_id AND ("isActive" = true OR "isActive" IS NULL)
        """
    )
    res = db.execute(q, {"store_id": store_id})
    out = []
    for row in res.mappings():
        out.append(dict(row))
    return out


def ensure_store_id_for_bundle(db: Session, bundle: BundleCreate) -> BundleCreate:
    if not bundle.store_id:
        sid = get_store_id_for_seller(db, bundle.seller_id)
        bundle.store_id = sid
    return bundle

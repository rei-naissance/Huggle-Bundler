from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException


def fetch_products_for_store(db: Session, store_id: str) -> List[Dict]:
    q = text(
        """
        SELECT id, name, "productType", "expiresOn", stock, tags
        FROM products
        WHERE "storeId" = :store_id AND ("isActive" = true OR "isActive" IS NULL)
        """
    )
    try:
        res = db.execute(q, {"store_id": store_id})
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database unavailable")
    out: List[Dict] = []
    for row in res.mappings():
        out.append(dict(row))
    return out

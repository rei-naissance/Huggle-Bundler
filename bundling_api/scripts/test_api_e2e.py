import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import settings
from app.main import app


def _find_any_seller_id():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        row = conn.execute(text('''
            SELECT s."sellerId"
            FROM stores s
            WHERE EXISTS (
                SELECT 1 FROM products p
                WHERE p."storeId" = s.id
                  AND (p."isActive" = true OR p."isActive" IS NULL)
                  AND COALESCE(p.stock, 0) > 0
            )
            LIMIT 1
        ''')).fetchone()
        return row[0] if row else None


def main():
    seller_id = _find_any_seller_id()
    if not seller_id:
        print("No stores found in DB; cannot test.")
        return

    client = TestClient(app)

    # 1) AI recommend (not saved)
    r = client.post("/bundles/recommend/ai", json={"seller_id": seller_id, "num_bundles": 2})
    print("AI RECOMMEND STATUS:", r.status_code)
    print("AI RECOMMEND BODY:", json.dumps(r.json(), indent=2)[:1500])

    # 2) AI recommend and save
    r2 = client.post("/bundles/recommend/ai/save", json={"seller_id": seller_id, "num_bundles": 2})
    print("AI SAVE STATUS:", r2.status_code)
    print("AI SAVE BODY:", json.dumps(r2.json(), indent=2)[:1500])


if __name__ == "__main__":
    main()

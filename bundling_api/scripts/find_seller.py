from sqlalchemy import create_engine, text
from app.config import settings

def main():
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
        print(row[0] if row else '')

if __name__ == '__main__':
    main()

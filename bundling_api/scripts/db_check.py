from sqlalchemy import create_engine, text
from app.config import settings

def main():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        exists_rs = conn.execute(text("""
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables 
              WHERE table_schema='public' AND table_name='bundles'
            )
        """))
        exists = list(exists_rs)[0][0]
        print('bundles_table_exists:', exists)
        if exists:
            cnt_rs = conn.execute(text('SELECT COUNT(*) FROM bundles'))
            cnt = list(cnt_rs)[0][0]
            print('bundles_row_count:', cnt)

if __name__ == '__main__':
    main()

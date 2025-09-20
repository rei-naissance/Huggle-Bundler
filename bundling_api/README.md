# Bundling API (FastAPI)

A standalone FastAPI service that recommends product bundles for sellers and can save them to Postgres.

Features (MVP):
- Rule-based bundling: expiry prioritization + category grouping
- Endpoints: recommend, save, get, list
- Postgres (Neon-ready) via SQLAlchemy
- Alembic migration for bundles table
- Dockerfile for deployment (Fly.io/Railway/AWS)

## Requirements
- Python 3.11+
- Postgres (DATABASE_URL)

## Setup
1) Create and activate a virtual environment, then install deps:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2) Configure environment:
   cp .env.example .env
   # Edit .env with your Neon/PG connection

3) Run Alembic migration to create the bundles table:
   alembic upgrade head

4) Start the API:
   uvicorn app.main:app --reload

API will be at http://localhost:8000

## Environment
- DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
- CORS_ORIGINS=*

## Endpoints
- POST /bundles/recommend
  Body: { "seller_id": "...", "num_bundles": 3 }
  Returns: array of candidate bundles (rule-based, not saved)

- POST /bundles/recommend/ai
  Body: { "seller_id": "...", "num_bundles": 3 }
  Returns: array of candidate bundles (AI-generated, not saved)

- POST /bundles/recommend/ai/save
  Body: { "seller_id": "...", "num_bundles": 3 }
  Returns: array of saved bundles (AI-generated and persisted)

- POST /bundles/save
  Body: BundleCreate
  Returns: saved bundle

- GET /bundles/{id}
  Returns: saved bundle by id

- GET /bundles?seller_id=...
  Returns: list of saved bundles for a seller

## Notes
- Uses existing products table (id, name, productType, expiresOn, stock, tags, storeId).
- For grouping, productType is used; fallback to tags or "Misc".
- Expiry prioritization: earlier expiresOn first; missing/"-infinity" treated as far future.

## Docker
Build & run:
  docker build -t bundling-api .
  docker run -p 8000:8000 --env-file .env bundling-api

## AI (optional)
You can enable AI-generated bundle names/descriptions via OpenRouter or Groq.

1) Set env vars in .env
   AI_PROVIDER=openrouter        # or groq
   OPENROUTER_API_KEY={{OPENROUTER_API_KEY}}  # do not commit
   OPENROUTER_MODEL=openrouter/auto
   GROQ_API_KEY={{GROQ_API_KEY}}             # do not commit
   GROQ_MODEL=llama3-8b-8192                 # example; set a valid Groq model

2) Start the API normally. If AI is configured, the recommender will enhance bundle name/description; if not, it will fall back to templates.

Security notes:
- Do NOT paste secrets into code or commit them. Use environment variables only.
- Rotate any keys that may have been shared in plain text.

## Neon setup
You do NOT need to run the provided schema.sql. Your Neon DB already has tables for stores/products/etc. Just run the migration to create the new bundles table.

1) Set DATABASE_URL in .env:
   DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<db>?sslmode=require

   If you have a psql URL that looks like:
   psql 'postgresql://USER:PASS@HOST/DB?sslmode=require&channel_binding=require'
   You can convert it by changing the prefix to postgresql+psycopg:// and keep the query params.

2) Run the migration:
   alembic upgrade head

3) Start the API:
   uvicorn app.main:app --reload


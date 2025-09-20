from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers.bundles import router as bundles_router

app = FastAPI(title="Bundling API", version="0.1.0")

# CORS
origins = [o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
app.include_router(bundles_router, prefix="/bundles", tags=["bundles"])

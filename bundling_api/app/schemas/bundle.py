from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    id: str
    name: str
    product_type: Optional[str] = Field(default=None, description="Category or type")
    expires_on: Optional[datetime] = None
    stock: int
    tags: List[str] = []


class BundleBase(BaseModel):
    name: str
    description: Optional[str] = None
    products: List[ProductIn]
    images: List[str] = []
    image_url: Optional[str] = None
    stock: int = 0


class BundleCreate(BundleBase):
    store_id: str


class BundleOut(BundleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendRequest(BaseModel):
    store_id: str
    num_bundles: int = 3


class AIRecommendRequest(BaseModel):
    store_id: str
    num_bundles: int = 3

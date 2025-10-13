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
    price: float = Field(description="Individual product price")
    original_price: Optional[float] = Field(default=None, description="Original price before any discounts")


class BundleBase(BaseModel):
    name: str
    description: Optional[str] = None
    products: List[ProductIn]
    images: List[str] = []
    image_url: Optional[str] = None
    stock: int = 0
    # Pricing fields
    price: Optional[float] = Field(default=None, description="Final bundle price after any discounts")
    original_price: Optional[float] = Field(default=None, description="Original total price of all products")
    total_cost: Optional[float] = Field(default=None, description="Total cost of bundle")


class BundleCreate(BundleBase):
    store_id: str


class BundleOut(BundleBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendRequest(BaseModel):
    store_id: str
    num_bundles: int = 3


class AIRecommendRequest(BaseModel):
    store_id: str
    num_bundles: int = 3

from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Bundle(Base):
    __tablename__ = "bundles"
    
    # Add unique constraint on store_id + signature for database-level deduplication
    __table_args__ = (
        UniqueConstraint('store_id', 'signature', name='uq_bundle_store_signature'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Scoping
    store_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    # Deduplication signature - SHA-256 hash of sorted product IDs
    signature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Content
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    products: Mapped[dict] = mapped_column(JSONB, nullable=False)  # list of product dicts
    images: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Main AI-generated image

    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

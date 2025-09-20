from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Bundle(Base):
    __tablename__ = "bundles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Scoping
    seller_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    store_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    # Content
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    products: Mapped[dict] = mapped_column(JSONB, nullable=False)  # list of product dicts
    images: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from __future__ import annotations
from typing import List, Optional

"""Config model — a collection of settings within a product."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Config(Base):
    __tablename__ = "configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="configs")  # noqa: F821
    settings: Mapped[List["Setting"]] = relationship(
        back_populates="config", cascade="all, delete-orphan"
    )  # noqa: F821
    sdk_keys: Mapped[List["SDKKey"]] = relationship(
        back_populates="config", cascade="all, delete-orphan"
    )  # noqa: F821

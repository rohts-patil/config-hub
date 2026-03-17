from __future__ import annotations
from typing import List, Optional

"""Environment model — represents a deployment stage (prod, staging, etc.)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#4CAF50")  # hex color
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        back_populates="environments"
    )  # noqa: F821
    setting_values: Mapped[List["SettingValue"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )  # noqa: F821
    sdk_keys: Mapped[List["SDKKey"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )  # noqa: F821

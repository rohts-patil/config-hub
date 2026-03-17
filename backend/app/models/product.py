from __future__ import annotations
from typing import List, Optional

"""Product model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="products"
    )  # noqa: F821
    configs: Mapped[List["Config"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # noqa: F821
    environments: Mapped[List["Environment"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # noqa: F821
    segments: Mapped[List["Segment"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # noqa: F821
    tags: Mapped[List["Tag"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # noqa: F821
    permission_groups: Mapped[List["PermissionGroup"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # noqa: F821
    webhooks: Mapped[List["Webhook"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # noqa: F821

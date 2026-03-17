from __future__ import annotations
from typing import List, Optional

"""Segment and SegmentCondition models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.targeting import Comparator


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="segments")  # noqa: F821
    conditions: Mapped[List["SegmentCondition"]] = relationship(back_populates="segment", cascade="all, delete-orphan")


class SegmentCondition(Base):
    __tablename__ = "segment_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    segment_id: Mapped[str] = mapped_column(String(36), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
    attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    comparator: Mapped[Comparator] = mapped_column(SAEnum(Comparator), nullable=False)
    comparison_value: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    segment: Mapped["Segment"] = relationship(back_populates="conditions")

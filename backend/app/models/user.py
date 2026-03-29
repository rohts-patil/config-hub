from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

"""User model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import OrganizationMember
    from app.models.permission import AuditLog


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    memberships: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="user"
    )  # noqa: F821
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")  # noqa: F821

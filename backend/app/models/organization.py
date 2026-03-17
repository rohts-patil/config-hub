from __future__ import annotations
from typing import List, Optional

"""Organization and OrganizationMember models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class OrgRole(str, enum.Enum):
    ADMIN = "admin"
    BILLING_MANAGER = "billing_manager"
    MEMBER = "member"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    members: Mapped[List["OrganizationMember"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    products: Mapped[List["Product"]] = relationship(back_populates="organization", cascade="all, delete-orphan")  # noqa: F821
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="organization", cascade="all, delete-orphan")  # noqa: F821


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[OrgRole] = mapped_column(SAEnum(OrgRole), default=OrgRole.MEMBER, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")  # noqa: F821

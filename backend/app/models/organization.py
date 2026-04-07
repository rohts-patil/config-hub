from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

"""Organization, OrganizationMember, and OrganizationInvite models."""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.permission import AuditLog
    from app.models.permission import ProductPermissionAssignment
    from app.models.product import Product
    from app.models.user import User


class OrgRole(str, enum.Enum):
    ADMIN = "admin"
    BILLING_MANAGER = "billing_manager"
    MEMBER = "member"


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    members: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    products: Mapped[List["Product"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )  # noqa: F821
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )  # noqa: F821
    invites: Mapped[List["OrganizationInvite"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[OrgRole] = mapped_column(
        SAEnum(OrgRole), default=OrgRole.MEMBER, nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")  # noqa: F821
    permission_assignments: Mapped[List["ProductPermissionAssignment"]] = relationship(
        back_populates="organization_member", cascade="all, delete-orphan"
    )


class OrganizationInvite(Base):
    __tablename__ = "organization_invites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        default=generate_invite_token,
    )
    role: Mapped[OrgRole] = mapped_column(
        SAEnum(OrgRole), default=OrgRole.MEMBER, nullable=False
    )
    invited_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_email_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="invites")

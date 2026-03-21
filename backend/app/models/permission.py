from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

"""Permission, Tag, SDKKey, AuditLog, Webhook models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.config import Config
    from app.models.environment import Environment
    from app.models.organization import Organization
    from app.models.product import Product
    from app.models.setting import Setting
    from app.models.user import User


class PermissionGroup(Base):
    __tablename__ = "permission_groups"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # permissions example: {"canManageFlags": true, "canManageEnvironments": false, ...}

    product: Mapped["Product"] = relationship(back_populates="permission_groups")  # noqa: F821


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#2196F3")

    product: Mapped["Product"] = relationship(back_populates="tags")  # noqa: F821
    settings: Mapped[List["SettingTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class SettingTag(Base):
    __tablename__ = "setting_tags"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    setting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("settings.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    setting: Mapped["Setting"] = relationship(back_populates="tags")  # noqa: F821
    tag: Mapped["Tag"] = relationship(back_populates="settings")


class SDKKey(Base):
    __tablename__ = "sdk_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("configs.id", ondelete="CASCADE"), nullable=False
    )
    environment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    config: Mapped["Config"] = relationship(back_populates="sdk_keys")  # noqa: F821
    environment: Mapped["Environment"] = relationship(back_populates="sdk_keys")  # noqa: F821


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # created, updated, deleted
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # setting, environment, etc.
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="audit_logs")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="audit_logs")  # noqa: F821


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    config_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("configs.id"), nullable=True
    )
    environment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("environments.id"), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    product: Mapped["Product"] = relationship(back_populates="webhooks")  # noqa: F821

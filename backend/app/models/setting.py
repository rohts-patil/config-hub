from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

"""Setting (feature flag) and SettingValue models."""

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.config import Config
    from app.models.environment import Environment
    from app.models.permission import SettingTag
    from app.models.targeting import PercentageOption, TargetingRule


class SettingType(str, enum.Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    INT = "int"
    DOUBLE = "double"


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("configs.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    setting_type: Mapped[SettingType] = mapped_column(
        SAEnum(SettingType), nullable=False, default=SettingType.BOOLEAN
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    config: Mapped["Config"] = relationship(back_populates="settings")  # noqa: F821
    values: Mapped[List["SettingValue"]] = relationship(
        back_populates="setting", cascade="all, delete-orphan"
    )
    tags: Mapped[List["SettingTag"]] = relationship(
        back_populates="setting", cascade="all, delete-orphan"
    )  # noqa: F821

    __table_args__ = (
        UniqueConstraint("config_id", "key", name="uq_setting_config_key"),
    )


class SettingValue(Base):
    """A setting's value and targeting rules for a specific environment."""

    __tablename__ = "setting_values"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    setting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("settings.id", ondelete="CASCADE"), nullable=False
    )
    environment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("environments.id", ondelete="CASCADE"), nullable=False
    )
    default_value: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # {"v": true/false/"str"/123}
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    setting: Mapped["Setting"] = relationship(back_populates="values")
    environment: Mapped["Environment"] = relationship(back_populates="setting_values")  # noqa: F821
    targeting_rules: Mapped[List["TargetingRule"]] = relationship(
        back_populates="setting_value", cascade="all, delete-orphan"
    )  # noqa: F821
    percentage_options: Mapped[List["PercentageOption"]] = relationship(
        back_populates="setting_value", cascade="all, delete-orphan"
    )  # noqa: F821

    __table_args__ = (
        UniqueConstraint("setting_id", "environment_id", name="uq_setting_value_env"),
    )

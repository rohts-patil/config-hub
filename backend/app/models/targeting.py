from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

"""Targeting rule, condition, and percentage option models."""

import uuid
import enum

from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.setting import SettingValue


class Comparator(str, enum.Enum):
    # Text
    EQUALS = "equals"
    NOT_EQUALS = "notEquals"
    CONTAINS = "contains"
    NOT_CONTAINS = "notContains"
    STARTS_WITH = "startsWith"
    NOT_STARTS_WITH = "notStartsWith"
    ENDS_WITH = "endsWith"
    NOT_ENDS_WITH = "notEndsWith"
    # List
    IS_ONE_OF = "isOneOf"
    IS_NOT_ONE_OF = "isNotOneOf"
    # Numeric
    NUMBER_EQUALS = "numberEquals"
    NUMBER_NOT_EQUALS = "numberNotEquals"
    NUMBER_LESS = "numberLess"
    NUMBER_LESS_OR_EQUALS = "numberLessOrEquals"
    NUMBER_GREATER = "numberGreater"
    NUMBER_GREATER_OR_EQUALS = "numberGreaterOrEquals"
    # Semver
    SEMVER_LESS = "semverLess"
    SEMVER_LESS_OR_EQUALS = "semverLessOrEquals"
    SEMVER_GREATER = "semverGreater"
    SEMVER_GREATER_OR_EQUALS = "semverGreaterOrEquals"
    SEMVER_EQUALS = "semverEquals"
    SEMVER_NOT_EQUALS = "semverNotEquals"
    # Datetime
    BEFORE = "before"
    AFTER = "after"
    # Regex
    REGEX_MATCH = "regexMatch"
    REGEX_NOT_MATCH = "regexNotMatch"
    # Array
    ARRAY_CONTAINS = "arrayContains"
    ARRAY_NOT_CONTAINS = "arrayNotContains"


class ConditionType(str, enum.Enum):
    USER = "user"
    FLAG = "flag"
    SEGMENT = "segment"


class TargetingRule(Base):
    __tablename__ = "targeting_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    setting_value_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("setting_values.id", ondelete="CASCADE"), nullable=False
    )
    served_value: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"v": ...}
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    setting_value: Mapped["SettingValue"] = relationship(
        back_populates="targeting_rules"
    )  # noqa: F821
    conditions: Mapped[List["Condition"]] = relationship(
        back_populates="targeting_rule", cascade="all, delete-orphan"
    )


class Condition(Base):
    __tablename__ = "conditions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    targeting_rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("targeting_rules.id", ondelete="CASCADE"), nullable=False
    )
    condition_type: Mapped[ConditionType] = mapped_column(
        SAEnum(ConditionType), default=ConditionType.USER, nullable=False
    )
    attribute: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # user attribute name
    comparator: Mapped[Comparator] = mapped_column(SAEnum(Comparator), nullable=False)
    comparison_value: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # {"v": "value"} or {"v": ["a","b"]}
    # For segment conditions
    segment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("segments.id"), nullable=True
    )
    # For flag prerequisite conditions
    prerequisite_setting_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("settings.id"), nullable=True
    )

    # Relationships
    targeting_rule: Mapped["TargetingRule"] = relationship(back_populates="conditions")


class PercentageOption(Base):
    __tablename__ = "percentage_options"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    setting_value_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("setting_values.id", ondelete="CASCADE"), nullable=False
    )
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    value: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"v": ...}
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    setting_value: Mapped["SettingValue"] = relationship(
        back_populates="percentage_options"
    )  # noqa: F821

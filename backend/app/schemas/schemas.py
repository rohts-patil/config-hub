from __future__ import annotations

"""Pydantic schemas for all API request/response models."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Organization ──────────────────────────────────────────────────────────────


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationOut(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgMemberOut(BaseModel):
    id: str
    user_id: str
    role: str
    user: UserOut | None = None

    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProductOut(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Config ────────────────────────────────────────────────────────────────────


class ConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    order: int | None = None


class ConfigOut(BaseModel):
    id: str
    product_id: str
    name: str
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Environment ───────────────────────────────────────────────────────────────


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    color: str = Field(default="#4CAF50", pattern=r"^#[0-9A-Fa-f]{6}$")


class EnvironmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    order: int | None = None


class EnvironmentOut(BaseModel):
    id: str
    product_id: str
    name: str
    color: str
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Setting (Feature Flag) ───────────────────────────────────────────────────


class SettingCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    name: str = Field(min_length=1, max_length=255)
    hint: str | None = None
    setting_type: str = Field(default="boolean")  # boolean, string, int, double


class SettingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    hint: str | None = None
    order: int | None = None


class SettingOut(BaseModel):
    id: str
    config_id: str
    key: str
    name: str
    hint: str | None
    setting_type: str
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Targeting Rules ──────────────────────────────────────────────────────────


class ConditionIn(BaseModel):
    condition_type: str = "user"  # user, flag, segment
    attribute: str | None = None
    comparator: str
    comparison_value: dict
    segment_id: str | None = None
    prerequisite_setting_id: str | None = None


class TargetingRuleIn(BaseModel):
    served_value: dict  # {"v": true/false/"str"/123}
    conditions: list[ConditionIn]
    order: int = 0


class PercentageOptionIn(BaseModel):
    percentage: int = Field(ge=0, le=100)
    value: dict  # {"v": ...}
    order: int = 0


class SettingValueUpdate(BaseModel):
    default_value: dict  # {"v": ...}
    targeting_rules: list[TargetingRuleIn] = []
    percentage_options: list[PercentageOptionIn] = []


class ConditionOut(BaseModel):
    id: str
    condition_type: str
    attribute: str | None
    comparator: str
    comparison_value: dict
    segment_id: str | None
    prerequisite_setting_id: str | None

    model_config = {"from_attributes": True}


class TargetingRuleOut(BaseModel):
    id: str
    served_value: dict
    order: int
    conditions: list[ConditionOut] = []

    model_config = {"from_attributes": True}


class PercentageOptionOut(BaseModel):
    id: str
    percentage: int
    value: dict
    order: int

    model_config = {"from_attributes": True}


class SettingValueOut(BaseModel):
    id: str
    setting_id: str
    environment_id: str
    default_value: dict | None
    updated_at: datetime
    targeting_rules: list[TargetingRuleOut] = []
    percentage_options: list[PercentageOptionOut] = []

    model_config = {"from_attributes": True}


# ── Segment ──────────────────────────────────────────────────────────────────


class SegmentConditionIn(BaseModel):
    attribute: str
    comparator: str
    comparison_value: dict


class SegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    conditions: list[SegmentConditionIn] = []


class SegmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    conditions: list[SegmentConditionIn] | None = None


class SegmentConditionOut(BaseModel):
    id: str
    attribute: str
    comparator: str
    comparison_value: dict

    model_config = {"from_attributes": True}


class SegmentOut(BaseModel):
    id: str
    product_id: str
    name: str
    description: str | None
    created_at: datetime
    conditions: list[SegmentConditionOut] = []

    model_config = {"from_attributes": True}


# ── SDK Key ──────────────────────────────────────────────────────────────────


class SDKKeyOut(BaseModel):
    id: str
    config_id: str
    environment_id: str
    key: str
    revoked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Audit Log ────────────────────────────────────────────────────────────────


class AuditLogOut(BaseModel):
    id: str
    organization_id: str
    user_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    old_value: dict | None
    new_value: dict | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Webhook ──────────────────────────────────────────────────────────────────


class WebhookCreate(BaseModel):
    url: str = Field(max_length=2048)
    config_id: str | None = None
    environment_id: str | None = None
    enabled: bool = True


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    config_id: str | None = None
    environment_id: str | None = None
    enabled: bool | None = None


class WebhookOut(BaseModel):
    id: str
    product_id: str
    url: str
    config_id: str | None
    environment_id: str | None
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Tag ──────────────────────────────────────────────────────────────────────


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    color: str = Field(default="#2196F3", pattern=r"^#[0-9A-Fa-f]{6}$")


class TagOut(BaseModel):
    id: str
    product_id: str
    name: str
    color: str

    model_config = {"from_attributes": True}

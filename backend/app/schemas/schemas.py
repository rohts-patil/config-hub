from __future__ import annotations

"""Pydantic schemas for all API request/response models."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditActorOut(BaseModel):
    id: str
    email: str
    name: str

    model_config = {"from_attributes": True}


class AuditContextOut(BaseModel):
    entity_label: Optional[str] = None
    entity_name: Optional[str] = None
    setting_key: Optional[str] = None
    setting_name: Optional[str] = None
    environment_name: Optional[str] = None
    config_name: Optional[str] = None
    product_name: Optional[str] = None


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
    user: Optional[UserOut] = None

    model_config = {"from_attributes": True}


class OrgMemberCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern=r"^(admin|billing_manager|member)$")


class OrgMemberUpdate(BaseModel):
    role: str = Field(pattern=r"^(admin|billing_manager|member)$")


# ── Product ───────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class ProductOut(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Config ────────────────────────────────────────────────────────────────────


class ConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    order: Optional[int] = None


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
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    order: Optional[int] = None


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
    hint: Optional[str] = None
    setting_type: str = Field(default="boolean")  # boolean, string, int, double


class SettingUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    hint: Optional[str] = None
    order: Optional[int] = None


class SettingOut(BaseModel):
    id: str
    config_id: str
    key: str
    name: str
    hint: Optional[str]
    setting_type: str
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Targeting Rules ──────────────────────────────────────────────────────────


class ConditionIn(BaseModel):
    condition_type: str = "user"  # user, flag, segment
    attribute: Optional[str] = None
    comparator: str
    comparison_value: dict
    segment_id: Optional[str] = None
    prerequisite_setting_id: Optional[str] = None


class TargetingRuleIn(BaseModel):
    served_value: dict  # {"v": true/false/"str"/123}
    conditions: List[ConditionIn]
    order: int = 0


class PercentageOptionIn(BaseModel):
    percentage: int = Field(ge=0, le=100)
    value: dict  # {"v": ...}
    order: int = 0


class SettingValueUpdate(BaseModel):
    default_value: dict  # {"v": ...}
    targeting_rules: List[TargetingRuleIn] = []
    percentage_options: List[PercentageOptionIn] = []


class ConditionOut(BaseModel):
    id: str
    condition_type: str
    attribute: Optional[str]
    comparator: str
    comparison_value: dict
    segment_id: Optional[str]
    prerequisite_setting_id: Optional[str]

    model_config = {"from_attributes": True}


class TargetingRuleOut(BaseModel):
    id: str
    served_value: dict
    order: int
    conditions: List[ConditionOut] = []

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
    default_value: Optional[dict]
    updated_at: datetime
    targeting_rules: List[TargetingRuleOut] = []
    percentage_options: List[PercentageOptionOut] = []

    model_config = {"from_attributes": True}


# ── Segment ──────────────────────────────────────────────────────────────────


class SegmentConditionIn(BaseModel):
    attribute: str
    comparator: str
    comparison_value: dict


class SegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    conditions: List[SegmentConditionIn] = []


class SegmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    conditions: Optional[List[SegmentConditionIn]] = None


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
    description: Optional[str]
    created_at: datetime
    conditions: List[SegmentConditionOut] = []

    model_config = {"from_attributes": True}


# ── SDK Key ──────────────────────────────────────────────────────────────────


class SDKKeySummaryOut(BaseModel):
    id: str
    config_id: str
    environment_id: str
    masked_key: str
    revoked: bool
    created_at: datetime


class SDKKeySecretOut(SDKKeySummaryOut):
    key: str


class SDKKeyCreate(BaseModel):
    config_id: str
    environment_id: str


# ── Audit Log ────────────────────────────────────────────────────────────────


class AuditLogOut(BaseModel):
    id: str
    organization_id: str
    user_id: Optional[str]
    user: Optional[AuditActorOut] = None
    context: Optional[AuditContextOut] = None
    action: str
    entity_type: str
    entity_id: Optional[str]
    old_value: Optional[dict]
    new_value: Optional[dict]
    reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Webhook ──────────────────────────────────────────────────────────────────


class WebhookCreate(BaseModel):
    url: str = Field(max_length=2048)
    config_id: Optional[str] = None
    environment_id: Optional[str] = None
    enabled: bool = True


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(default=None, max_length=2048)
    config_id: Optional[str] = None
    environment_id: Optional[str] = None
    enabled: Optional[bool] = None


class WebhookOut(BaseModel):
    id: str
    product_id: str
    url: str
    config_id: Optional[str]
    environment_id: Optional[str]
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

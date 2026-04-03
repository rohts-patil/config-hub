from __future__ import annotations
from typing import List, Optional

"""Audit log router — list with filters."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.config import Config
from app.models.environment import Environment
from app.models.organization import OrganizationInvite, OrganizationMember
from app.models.permission import (
    AuditLog,
    PermissionGroup,
    SDKKey,
    Tag,
    Webhook,
)
from app.models.product import Product
from app.models.segment import Segment
from app.models.setting import Setting, SettingValue
from app.database import get_db
from app.models.user import User
from app.schemas.schemas import AuditLogOut
from app.services.auth import get_current_user
from app.services.authz import get_org_product_ids_with_permission, require_org_member

router = APIRouter(
    prefix="/api/v1/organizations/{org_id}/audit-log", tags=["Audit Log"]
)


@router.get("", response_model=List[AuditLogOut])
async def list_audit_logs(
    org_id: str,
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_org_member(db, org_id, current_user)
    accessible_product_ids = await get_org_product_ids_with_permission(
        db, org_id, current_user, "canViewAuditLog"
    )

    if accessible_product_ids == set():
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this organization's audit log",
        )

    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.organization_id == org_id)
    )
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.created_at.desc())
    if accessible_product_ids is not None:
        query = query.where(AuditLog.product_id.in_(accessible_product_ids))
        query = query.offset(offset).limit(limit)
    else:
        query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()
    context_by_entity_id = await _build_audit_context(db, logs)

    enriched_logs = []
    for log in logs:
        payload = AuditLogOut.model_validate(log).model_dump()
        if log.entity_id:
            payload["context"] = context_by_entity_id.get(log.entity_id)
        enriched_logs.append(AuditLogOut(**payload))

    return enriched_logs


async def _build_audit_context(
    db: AsyncSession, logs: list[AuditLog]
) -> dict[str, dict]:
    entity_ids_by_type: dict[str, set[str]] = {}
    for log in logs:
        if not log.entity_id:
            continue
        entity_ids_by_type.setdefault(log.entity_type, set()).add(log.entity_id)

    context_by_entity_id: dict[str, dict] = {}

    if config_ids := entity_ids_by_type.get("config"):
        result = await db.execute(select(Config).where(Config.id.in_(config_ids)))
        for config in result.scalars().all():
            context_by_entity_id[config.id] = {
                "entity_label": config.name,
                "entity_name": config.name,
                "config_name": config.name,
            }

    if product_ids := entity_ids_by_type.get("product"):
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for product in result.scalars().all():
            context_by_entity_id[product.id] = {
                "entity_label": product.name,
                "entity_name": product.name,
                "product_name": product.name,
            }

    if environment_ids := entity_ids_by_type.get("environment"):
        result = await db.execute(
            select(Environment).where(Environment.id.in_(environment_ids))
        )
        for environment in result.scalars().all():
            context_by_entity_id[environment.id] = {
                "entity_label": environment.name,
                "entity_name": environment.name,
                "environment_name": environment.name,
            }

    if setting_ids := entity_ids_by_type.get("setting"):
        result = await db.execute(select(Setting).where(Setting.id.in_(setting_ids)))
        for setting in result.scalars().all():
            context_by_entity_id[setting.id] = {
                "entity_label": setting.key,
                "entity_name": setting.name,
                "setting_key": setting.key,
                "setting_name": setting.name,
            }

    if segment_ids := entity_ids_by_type.get("segment"):
        result = await db.execute(select(Segment).where(Segment.id.in_(segment_ids)))
        for segment in result.scalars().all():
            context_by_entity_id[segment.id] = {
                "entity_label": segment.name,
                "entity_name": segment.name,
            }

    if tag_ids := entity_ids_by_type.get("tag"):
        result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        for tag in result.scalars().all():
            context_by_entity_id[tag.id] = {
                "entity_label": tag.name,
                "entity_name": tag.name,
            }

    if sdk_key_ids := entity_ids_by_type.get("sdk_key"):
        result = await db.execute(
            select(SDKKey)
            .options(selectinload(SDKKey.config), selectinload(SDKKey.environment))
            .where(SDKKey.id.in_(sdk_key_ids))
        )
        for sdk_key in result.scalars().all():
            config_name = sdk_key.config.name if sdk_key.config else None
            environment_name = sdk_key.environment.name if sdk_key.environment else None
            label_parts = [part for part in [config_name, environment_name] if part]
            context_by_entity_id[sdk_key.id] = {
                "entity_label": " / ".join(label_parts) if label_parts else None,
                "config_name": config_name,
                "environment_name": environment_name,
            }

    if webhook_ids := entity_ids_by_type.get("webhook"):
        result = await db.execute(select(Webhook).where(Webhook.id.in_(webhook_ids)))
        for webhook in result.scalars().all():
            context_by_entity_id[webhook.id] = {
                "entity_label": webhook.url,
                "entity_name": webhook.url,
            }

    if permission_group_ids := entity_ids_by_type.get("permission_group"):
        result = await db.execute(
            select(PermissionGroup).where(PermissionGroup.id.in_(permission_group_ids))
        )
        for group in result.scalars().all():
            context_by_entity_id[group.id] = {
                "entity_label": group.name,
                "entity_name": group.name,
            }

    if member_ids := entity_ids_by_type.get("organization_member"):
        result = await db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(OrganizationMember.id.in_(member_ids))
        )
        for member in result.scalars().all():
            user_label = member.user.email if member.user else None
            context_by_entity_id[member.id] = {
                "entity_label": user_label,
                "entity_name": user_label,
            }

    if assignment_member_ids := entity_ids_by_type.get("permission_assignment"):
        result = await db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(OrganizationMember.id.in_(assignment_member_ids))
        )
        for member in result.scalars().all():
            user_label = member.user.email if member.user else None
            context_by_entity_id[member.id] = {
                "entity_label": user_label,
                "entity_name": user_label,
            }

    if invite_ids := entity_ids_by_type.get("organization_invite"):
        result = await db.execute(
            select(OrganizationInvite).where(OrganizationInvite.id.in_(invite_ids))
        )
        for invite in result.scalars().all():
            context_by_entity_id[invite.id] = {
                "entity_label": invite.email,
                "entity_name": invite.email,
            }

    if setting_value_ids := entity_ids_by_type.get("setting_value"):
        result = await db.execute(
            select(SettingValue)
            .options(
                selectinload(SettingValue.setting),
                selectinload(SettingValue.environment),
            )
            .where(SettingValue.id.in_(setting_value_ids))
        )
        for setting_value in result.scalars().all():
            setting_key = setting_value.setting.key if setting_value.setting else None
            setting_name = setting_value.setting.name if setting_value.setting else None
            environment_name = (
                setting_value.environment.name if setting_value.environment else None
            )
            label_parts = [part for part in [setting_key, environment_name] if part]
            context_by_entity_id[setting_value.id] = {
                "entity_label": " in ".join(label_parts) if label_parts else None,
                "setting_key": setting_key,
                "setting_name": setting_name,
                "environment_name": environment_name,
            }

    return context_by_entity_id

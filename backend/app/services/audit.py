"""Audit log auto-recording service.

Usage in routers:
    from app.services.audit import record_audit

    await record_audit(
        db=db,
        org_id=org_id,
        user_id=current_user.id,
        action="updated",
        entity_type="setting",
        entity_id=setting.id,
        old_value={"name": old_name},
        new_value={"name": new_name},
    )
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import AuditLog


async def record_audit(
    db: AsyncSession,
    org_id: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    reason: Optional[str] = None,
) -> AuditLog:
    """Insert an audit log entry. Should be called inside the same transaction."""
    entry = AuditLog(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_org_id_for_product(db: AsyncSession, product_id: str) -> Optional[str]:
    """Resolve product_id → organization_id."""
    from app.models.product import Product
    from sqlalchemy import select

    result = await db.execute(select(Product.organization_id).where(Product.id == product_id))
    row = result.scalar_one_or_none()
    return row


async def get_org_id_for_config(db: AsyncSession, config_id: str) -> Optional[str]:
    """Resolve config_id → organization_id via product."""
    from app.models.config import Config
    from app.models.product import Product
    from sqlalchemy import select

    result = await db.execute(
        select(Product.organization_id)
        .join(Config, Config.product_id == Product.id)
        .where(Config.id == config_id)
    )
    return result.scalar_one_or_none()


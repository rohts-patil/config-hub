from __future__ import annotations
from typing import List

"""Webhook router — CRUD under a product."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.permission import Webhook, WebhookDeliveryAttempt
from app.schemas.schemas import (
    WebhookCreate,
    WebhookDeliveryAttemptOut,
    WebhookOut,
    WebhookUpdate,
)
from app.services.auth import get_current_user
from app.services.audit import get_org_id_for_product, record_audit
from app.services.authz import require_product_permission

router = APIRouter(prefix="/api/v1/products/{product_id}/webhooks", tags=["Webhooks"])


@router.get("", response_model=List[WebhookOut])
async def list_webhooks(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageWebhooks")
    result = await db.execute(select(Webhook).where(Webhook.product_id == product_id))
    return result.scalars().all()


@router.post("", response_model=WebhookOut, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    product_id: str,
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageWebhooks")
    webhook_kwargs = {
        "product_id": product_id,
        "url": body.url,
        "config_id": body.config_id,
        "environment_id": body.environment_id,
        "enabled": body.enabled,
    }
    if body.signing_secret:
        webhook_kwargs["signing_secret"] = body.signing_secret

    webhook = Webhook(
        **webhook_kwargs,
    )
    db.add(webhook)
    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "webhook",
            product_id=product_id,
            entity_id=webhook.id,
            new_value={
                "url": webhook.url,
                "config_id": webhook.config_id,
                "environment_id": webhook.environment_id,
                "signing_secret_configured": bool(webhook.signing_secret),
                "enabled": webhook.enabled,
            },
        )
    return webhook


@router.get("/{webhook_id}", response_model=WebhookOut)
async def get_webhook(
    product_id: str,
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageWebhooks")
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.product_id == product_id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookOut)
async def update_webhook(
    product_id: str,
    webhook_id: str,
    body: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageWebhooks")
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.product_id == product_id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    old_value = {
        "url": webhook.url,
        "config_id": webhook.config_id,
        "environment_id": webhook.environment_id,
        "signing_secret_configured": bool(webhook.signing_secret),
        "enabled": webhook.enabled,
    }
    if body.url is not None:
        webhook.url = body.url
    if body.config_id is not None:
        webhook.config_id = body.config_id
    if body.environment_id is not None:
        webhook.environment_id = body.environment_id
    if body.signing_secret is not None:
        webhook.signing_secret = body.signing_secret
    if body.enabled is not None:
        webhook.enabled = body.enabled
    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "webhook",
            product_id=product_id,
            entity_id=webhook.id,
            old_value=old_value,
            new_value={
                "url": webhook.url,
                "config_id": webhook.config_id,
                "environment_id": webhook.environment_id,
                "signing_secret_configured": bool(webhook.signing_secret),
                "enabled": webhook.enabled,
            },
        )
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    product_id: str,
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageWebhooks")
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.product_id == product_id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "webhook",
            product_id=product_id,
            entity_id=webhook.id,
            old_value={
                "url": webhook.url,
                "config_id": webhook.config_id,
                "environment_id": webhook.environment_id,
                "signing_secret_configured": bool(webhook.signing_secret),
                "enabled": webhook.enabled,
            },
        )
    await db.delete(webhook)


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryAttemptOut])
async def list_webhook_deliveries(
    product_id: str,
    webhook_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageWebhooks")
    webhook = await _load_webhook(product_id, webhook_id, db)
    result = await db.execute(
        select(WebhookDeliveryAttempt)
        .where(WebhookDeliveryAttempt.webhook_id == webhook.id)
        .order_by(WebhookDeliveryAttempt.created_at.desc())
        .limit(min(max(limit, 1), 50))
    )
    return result.scalars().all()


async def _load_webhook(product_id: str, webhook_id: str, db: AsyncSession) -> Webhook:
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.product_id == product_id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook

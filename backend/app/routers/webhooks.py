from __future__ import annotations
from typing import List

"""Webhook router — CRUD under a product."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.permission import Webhook
from app.schemas.schemas import WebhookCreate, WebhookUpdate, WebhookOut
from app.services.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/products/{product_id}/webhooks", tags=["Webhooks"]
)


@router.get("", response_model=List[WebhookOut])
async def list_webhooks(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Webhook).where(Webhook.product_id == product_id)
    )
    return result.scalars().all()


@router.post("", response_model=WebhookOut, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    product_id: str,
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    webhook = Webhook(
        product_id=product_id,
        url=body.url,
        config_id=body.config_id,
        environment_id=body.environment_id,
        enabled=body.enabled,
    )
    db.add(webhook)
    await db.flush()
    return webhook


@router.get("/{webhook_id}", response_model=WebhookOut)
async def get_webhook(
    product_id: str,
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.product_id == product_id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if body.url is not None:
        webhook.url = body.url
    if body.config_id is not None:
        webhook.config_id = body.config_id
    if body.environment_id is not None:
        webhook.environment_id = body.environment_id
    if body.enabled is not None:
        webhook.enabled = body.enabled
    await db.flush()
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    product_id: str,
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.product_id == product_id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)


"""Webhook async dispatcher with retry and exponential backoff.

Dispatches HTTP POST to all matching webhooks when a flag/config change occurs.
Runs in a background task so the API response is not delayed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Webhook

logger = logging.getLogger("confighub.webhooks")

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds — 2, 4, 8


async def dispatch_webhooks(
    db: AsyncSession,
    product_id: str,
    event: str,
    payload: dict,
    config_id: Optional[str] = None,
    environment_id: Optional[str] = None,
) -> None:
    """Find matching enabled webhooks and fire them in background tasks."""
    query = select(Webhook).where(
        Webhook.product_id == product_id,
        Webhook.enabled == True,  # noqa: E712
    )
    if config_id:
        # Match webhooks that target this specific config OR have no filter
        query = query.where(
            (Webhook.config_id == config_id) | (Webhook.config_id == None)  # noqa: E711
        )
    if environment_id:
        query = query.where(
            (Webhook.environment_id == environment_id) | (Webhook.environment_id == None)  # noqa: E711
        )

    result = await db.execute(query)
    webhooks = result.scalars().all()

    if not webhooks:
        return

    body = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }

    for wh in webhooks:
        # Fire-and-forget background task
        asyncio.create_task(_send_webhook(wh.url, body))


async def _send_webhook(url: str, body: dict) -> None:
    """POST the payload with retry and exponential backoff."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code < 400:
                    logger.info("Webhook delivered to %s (status %d)", url, resp.status_code)
                    return
                logger.warning(
                    "Webhook %s returned %d (attempt %d/%d)",
                    url, resp.status_code, attempt + 1, MAX_RETRIES + 1,
                )
        except Exception as exc:
            logger.warning(
                "Webhook %s failed (attempt %d/%d): %s",
                url, attempt + 1, MAX_RETRIES + 1, exc,
            )

        if attempt < MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE ** (attempt + 1))

    logger.error("Webhook %s exhausted all retries", url)


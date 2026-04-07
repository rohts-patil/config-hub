"""Webhook async dispatcher with retry and exponential backoff.

Dispatches HTTP POST to all matching webhooks when a flag/config change occurs.
Runs in a background task so the API response is not delayed.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.permission import Webhook, WebhookDeliveryAttempt

logger = logging.getLogger("confighub.webhooks")

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds — 2, 4, 8
MAX_RESPONSE_BODY_LENGTH = 2000


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
            (Webhook.environment_id == environment_id)
            | (Webhook.environment_id == None)  # noqa: E711
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
    body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)

    for wh in webhooks:
        # Fire-and-forget background task
        asyncio.create_task(
            _send_webhook(
                webhook_id=wh.id,
                url=wh.url,
                event=event,
                timestamp=body["timestamp"],
                body_json=body_json,
                signing_secret=wh.signing_secret,
            )
        )


async def _send_webhook(
    *,
    webhook_id: str,
    url: str,
    event: str,
    timestamp: str,
    body_json: str,
    signing_secret: str,
) -> None:
    """POST the payload with retry and exponential backoff."""
    headers = {
        "Content-Type": "application/json",
        "X-ConfigHub-Event": event,
        "X-ConfigHub-Timestamp": timestamp,
        "X-ConfigHub-Signature-256": _sign_webhook_payload(
            signing_secret,
            timestamp,
            body_json,
        ),
    }

    for attempt in range(1, MAX_RETRIES + 2):
        status_code = None
        response_body = None
        error_message = None
        delivered_at = None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    content=body_json,
                    headers=headers,
                )
                status_code = resp.status_code
                response_body = _truncate_text(resp.text)
                if resp.status_code < 400:
                    delivered_at = datetime.now(timezone.utc)
                    await _record_delivery_attempt(
                        webhook_id=webhook_id,
                        event=event,
                        attempt_number=attempt,
                        status_code=status_code,
                        response_body=response_body,
                        error_message=None,
                        delivered_at=delivered_at,
                    )
                    logger.info(
                        "Webhook delivered to %s (status %d)", url, resp.status_code
                    )
                    return
                error_message = f"Received HTTP {resp.status_code}"
                logger.warning(
                    "Webhook %s returned %d (attempt %d/%d)",
                    url,
                    resp.status_code,
                    attempt,
                    MAX_RETRIES + 1,
                )
        except Exception as exc:
            error_message = str(exc)
            logger.warning(
                "Webhook %s failed (attempt %d/%d): %s",
                url,
                attempt,
                MAX_RETRIES + 1,
                exc,
            )

        await _record_delivery_attempt(
            webhook_id=webhook_id,
            event=event,
            attempt_number=attempt,
            status_code=status_code,
            response_body=response_body,
            error_message=error_message,
            delivered_at=delivered_at,
        )

        if attempt <= MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE**attempt)

    logger.error("Webhook %s exhausted all retries", url)


def _sign_webhook_payload(signing_secret: str, timestamp: str, body_json: str) -> str:
    payload = f"{timestamp}.{body_json}".encode()
    digest = hmac.new(signing_secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def _record_delivery_attempt(
    *,
    webhook_id: str,
    event: str,
    attempt_number: int,
    status_code: int | None,
    response_body: str | None,
    error_message: str | None,
    delivered_at: datetime | None,
) -> None:
    try:
        async with async_session() as session:
            session.add(
                WebhookDeliveryAttempt(
                    webhook_id=webhook_id,
                    event=event,
                    attempt_number=attempt_number,
                    status_code=status_code,
                    response_body=response_body,
                    error_message=error_message,
                    delivered_at=delivered_at,
                )
            )
            await session.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to persist webhook delivery attempt: %s", exc)


def _truncate_text(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= MAX_RESPONSE_BODY_LENGTH:
        return value
    return value[: MAX_RESPONSE_BODY_LENGTH - 3] + "..."

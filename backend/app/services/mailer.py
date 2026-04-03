from __future__ import annotations

"""SMTP mail delivery helpers."""

import asyncio
import smtplib
from email.message import EmailMessage

from app.config import settings


class EmailConfigurationError(RuntimeError):
    """Raised when SMTP is not configured."""


class EmailDeliveryError(RuntimeError):
    """Raised when SMTP delivery fails."""


async def send_email(*, recipient: str, subject: str, text_body: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise EmailConfigurationError(
            "SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL to send invite emails."
        )

    await asyncio.to_thread(
        _send_email_sync,
        recipient=recipient,
        subject=subject,
        text_body=text_body,
    )


def _send_email_sync(*, recipient: str, subject: str, text_body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(text_body)

    try:
        if settings.SMTP_USE_SSL:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=15,
            )
        else:
            smtp = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=15,
            )

        with smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover
        raise EmailDeliveryError(f"Failed to send email: {exc}") from exc

from __future__ import annotations

"""Helpers for organization invite lifecycle."""

from datetime import datetime, timezone
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.organization import Organization, OrganizationInvite, OrganizationMember
from app.models.user import User
from app.services.audit import record_audit
from app.services.mailer import EmailConfigurationError, send_email


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def send_org_invite_email(
    invite: OrganizationInvite,
    organization: Organization,
    inviter: User,
) -> None:
    if not settings.INVITE_EMAILS_ENABLED:
        invite.email_sent_at = None
        invite.last_email_error = None
        return

    signup_url = (
        f"{settings.FRONTEND_APP_URL.rstrip('/')}/register?email={quote(invite.email)}"
    )
    login_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/login"
    inviter_label = inviter.name.strip() if inviter.name.strip() else inviter.email
    template_context = {
        "organization_name": organization.name,
        "inviter_name": inviter_label,
        "role_name": invite.role.value.replace("_", " "),
        "signup_url": signup_url,
        "login_url": login_url,
        "invitee_email": invite.email,
    }
    try:
        subject = settings.INVITE_EMAIL_SUBJECT_TEMPLATE.format(**template_context)
        text_body = settings.INVITE_EMAIL_BODY_TEMPLATE.format(**template_context)
    except KeyError as exc:
        raise EmailConfigurationError(
            f"Invalid invite email template placeholder: {exc.args[0]}"
        ) from exc
    await send_email(recipient=invite.email, subject=subject, text_body=text_body)
    invite.email_sent_at = datetime.now(timezone.utc)
    invite.last_email_error = None


async def accept_pending_org_invites(db: AsyncSession, user: User) -> int:
    normalized_email = normalize_email(user.email)
    invite_result = await db.execute(
        select(OrganizationInvite).where(
            func.lower(OrganizationInvite.email) == normalized_email
        )
    )
    invites = invite_result.scalars().all()
    accepted_count = 0

    for invite in invites:
        membership_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == invite.organization_id,
                OrganizationMember.user_id == user.id,
            )
        )
        membership = membership_result.scalar_one_or_none()

        if membership is None:
            membership = OrganizationMember(
                organization_id=invite.organization_id,
                user_id=user.id,
                role=invite.role,
            )
            db.add(membership)
            await db.flush()

            await record_audit(
                db,
                invite.organization_id,
                user.id,
                "accepted",
                "organization_invite",
                entity_id=invite.id,
                new_value={
                    "email": normalized_email,
                    "role": invite.role.value,
                    "user_id": user.id,
                },
            )
            accepted_count += 1

        await db.delete(invite)

    return accepted_count

from __future__ import annotations

"""Helpers for organization invite lifecycle."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrganizationInvite, OrganizationMember
from app.models.user import User
from app.services.audit import record_audit


def normalize_email(email: str) -> str:
    return email.strip().lower()


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

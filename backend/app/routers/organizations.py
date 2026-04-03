from __future__ import annotations
from typing import List

"""Organization router — CRUD + member management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.schemas.schemas import (
    OrgMemberCreate,
    OrgMemberUpdate,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationOut,
    OrgMemberOut,
)
from app.services.audit import record_audit
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


async def _get_org_as_member(org_id: str, user: User, db: AsyncSession) -> Organization:
    """Fetch org ensuring the current user is a member."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return org


async def _get_org_membership(
    org_id: str, user_id: str, db: AsyncSession
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _require_org_admin(
    org_id: str, user: User, db: AsyncSession
) -> Organization:
    org = await _get_org_as_member(org_id, user, db)
    membership = await _get_org_membership(org_id, user.id, db)
    if membership is None or membership.role != OrgRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only organization admins can manage members"
        )
    return org


async def _get_member_by_id(
    org_id: str, member_id: str, db: AsyncSession
) -> OrganizationMember:
    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.id == member_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Organization member not found")
    return member


async def _count_org_admins(org_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.role == OrgRole.ADMIN,
        )
    )
    return len(result.scalars().all())


async def _ensure_member_change_keeps_admin(
    org_id: str,
    member: OrganizationMember,
    db: AsyncSession,
    *,
    next_role: OrgRole | None = None,
) -> None:
    removing_admin_role = (
        member.role == OrgRole.ADMIN and next_role is not None and next_role != OrgRole.ADMIN
    )
    removing_member = member.role == OrgRole.ADMIN and next_role is None
    if not removing_admin_role and not removing_member:
        return

    admin_count = await _count_org_admins(org_id, db)
    if admin_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Organizations must always have at least one admin",
        )


@router.get("", response_model=List[OrganizationOut])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = Organization(name=body.name)
    db.add(org)
    await db.flush()
    # Auto-add creator as admin
    member = OrganizationMember(
        organization_id=org.id, user_id=current_user.id, role=OrgRole.ADMIN
    )
    db.add(member)
    await db.flush()
    return org


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_org_as_member(org_id, current_user, db)


@router.patch("/{org_id}", response_model=OrganizationOut)
async def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await _require_org_admin(org_id, current_user, db)
    org.name = body.name
    await db.flush()
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await _require_org_admin(org_id, current_user, db)
    await db.delete(org)


@router.get("/{org_id}/members", response_model=List[OrgMemberOut])
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_org_as_member(org_id, current_user, db)
    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(OrganizationMember.organization_id == org_id)
    )
    return result.scalars().all()


@router.post(
    "/{org_id}/members",
    response_model=OrgMemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    org_id: str,
    body: OrgMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_admin(org_id, current_user, db)

    user_result = await db.execute(select(User).where(User.email == body.email))
    invited_user = user_result.scalar_one_or_none()
    if invited_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found. Ask them to sign up first, then add them here.",
        )

    existing_member = await _get_org_membership(org_id, invited_user.id, db)
    if existing_member is not None:
        raise HTTPException(
            status_code=400, detail="That user is already a member of this organization"
        )

    member = OrganizationMember(
        organization_id=org_id,
        user_id=invited_user.id,
        role=OrgRole(body.role),
    )
    db.add(member)
    await db.flush()

    member_result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(OrganizationMember.id == member.id)
    )
    created_member = member_result.scalar_one()

    await record_audit(
        db,
        org_id,
        current_user.id,
        "created",
        "organization_member",
        entity_id=member.id,
        new_value={
            "email": invited_user.email,
            "role": member.role.value,
            "user_id": invited_user.id,
        },
    )

    return created_member


@router.patch("/{org_id}/members/{member_id}", response_model=OrgMemberOut)
async def update_member(
    org_id: str,
    member_id: str,
    body: OrgMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_admin(org_id, current_user, db)
    member = await _get_member_by_id(org_id, member_id, db)
    next_role = OrgRole(body.role)
    if member.role == next_role:
        return member

    await _ensure_member_change_keeps_admin(
        org_id,
        member,
        db,
        next_role=next_role,
    )

    old_role = member.role
    member.role = next_role
    await db.flush()

    await record_audit(
        db,
        org_id,
        current_user.id,
        "updated",
        "organization_member",
        entity_id=member.id,
        old_value={"role": old_role.value, "user_id": member.user_id},
        new_value={"role": member.role.value, "user_id": member.user_id},
    )

    refreshed_member = await _get_member_by_id(org_id, member.id, db)
    return refreshed_member


@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    org_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_admin(org_id, current_user, db)
    member = await _get_member_by_id(org_id, member_id, db)

    await _ensure_member_change_keeps_admin(org_id, member, db)

    await record_audit(
        db,
        org_id,
        current_user.id,
        "deleted",
        "organization_member",
        entity_id=member.id,
        old_value={
            "role": member.role.value,
            "user_id": member.user_id,
            "email": member.user.email if member.user else None,
        },
    )

    await db.delete(member)

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
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationOut,
    OrgMemberOut,
)
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
    org = await _get_org_as_member(org_id, current_user, db)
    org.name = body.name
    await db.flush()
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await _get_org_as_member(org_id, current_user, db)
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

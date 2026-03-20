from __future__ import annotations
from typing import List, Optional

"""Audit log router — list with filters."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.permission import AuditLog
from app.schemas.schemas import AuditLogOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/v1/organizations/{org_id}/audit-log", tags=["Audit Log"])


async def _require_org_member(org_id: str, user: User, db: AsyncSession):
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")


@router.get("", response_model=List[AuditLogOut])
async def list_audit_logs(
    org_id: str,
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_org_member(org_id, current_user, db)
    query = select(AuditLog).where(AuditLog.organization_id == org_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


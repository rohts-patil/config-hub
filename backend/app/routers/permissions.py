from __future__ import annotations
from typing import List

"""Permission group router — CRUD under a product."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.permission import PermissionGroup
from app.services.auth import get_current_user
from app.services.audit import get_org_id_for_product, record_audit
from app.services.authz import require_product_member

router = APIRouter(
    prefix="/api/v1/products/{product_id}/permissions", tags=["Permissions"]
)


class PermissionGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    permissions: dict = {}


class PermissionGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    permissions: Optional[dict] = None


class PermissionGroupOut(BaseModel):
    id: str
    product_id: str
    name: str
    permissions: dict

    model_config = {"from_attributes": True}


@router.get("", response_model=List[PermissionGroupOut])
async def list_permission_groups(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(PermissionGroup).where(PermissionGroup.product_id == product_id)
    )
    return result.scalars().all()


@router.post("", response_model=PermissionGroupOut, status_code=status.HTTP_201_CREATED)
async def create_permission_group(
    product_id: str,
    body: PermissionGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    pg = PermissionGroup(
        product_id=product_id, name=body.name, permissions=body.permissions
    )
    db.add(pg)
    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "permission_group",
            entity_id=pg.id,
            new_value={"name": pg.name, "permissions": pg.permissions},
        )
    return pg


@router.patch("/{group_id}", response_model=PermissionGroupOut)
async def update_permission_group(
    product_id: str,
    group_id: str,
    body: PermissionGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(PermissionGroup).where(
            PermissionGroup.id == group_id,
            PermissionGroup.product_id == product_id,
        )
    )
    pg = result.scalar_one_or_none()
    if not pg:
        raise HTTPException(status_code=404, detail="Permission group not found")
    old_value = {"name": pg.name, "permissions": pg.permissions}
    if body.name is not None:
        pg.name = body.name
    if body.permissions is not None:
        pg.permissions = body.permissions
    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "permission_group",
            entity_id=pg.id,
            old_value=old_value,
            new_value={"name": pg.name, "permissions": pg.permissions},
        )
    return pg


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission_group(
    product_id: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(PermissionGroup).where(
            PermissionGroup.id == group_id,
            PermissionGroup.product_id == product_id,
        )
    )
    pg = result.scalar_one_or_none()
    if not pg:
        raise HTTPException(status_code=404, detail="Permission group not found")
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "permission_group",
            entity_id=pg.id,
            old_value={"name": pg.name, "permissions": pg.permissions},
        )
    await db.delete(pg)

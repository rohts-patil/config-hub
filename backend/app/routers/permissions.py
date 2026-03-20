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
    pg = PermissionGroup(
        product_id=product_id, name=body.name, permissions=body.permissions
    )
    db.add(pg)
    await db.flush()
    return pg


@router.patch("/{group_id}", response_model=PermissionGroupOut)
async def update_permission_group(
    product_id: str,
    group_id: str,
    body: PermissionGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PermissionGroup).where(
            PermissionGroup.id == group_id,
            PermissionGroup.product_id == product_id,
        )
    )
    pg = result.scalar_one_or_none()
    if not pg:
        raise HTTPException(status_code=404, detail="Permission group not found")
    if body.name is not None:
        pg.name = body.name
    if body.permissions is not None:
        pg.permissions = body.permissions
    await db.flush()
    return pg


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission_group(
    product_id: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PermissionGroup).where(
            PermissionGroup.id == group_id,
            PermissionGroup.product_id == product_id,
        )
    )
    pg = result.scalar_one_or_none()
    if not pg:
        raise HTTPException(status_code=404, detail="Permission group not found")
    await db.delete(pg)


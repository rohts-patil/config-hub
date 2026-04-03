from __future__ import annotations
from typing import List

"""Tag router — CRUD under a product."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.permission import Tag
from app.schemas.schemas import TagCreate, TagOut
from app.services.auth import get_current_user
from app.services.audit import get_org_id_for_product, record_audit
from app.services.authz import require_product_member, require_product_permission

router = APIRouter(prefix="/api/v1/products/{product_id}/tags", tags=["Tags"])


@router.get("", response_model=List[TagOut])
async def list_tags(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(select(Tag).where(Tag.product_id == product_id))
    return result.scalars().all()


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(
    product_id: str,
    body: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageTags")
    tag = Tag(product_id=product_id, name=body.name, color=body.color)
    db.add(tag)
    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "tag",
            entity_id=tag.id,
            new_value={"name": tag.name, "color": tag.color},
        )
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    product_id: str,
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageTags")
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.product_id == product_id)
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "tag",
            entity_id=tag.id,
            old_value={"name": tag.name, "color": tag.color},
        )
    await db.delete(tag)

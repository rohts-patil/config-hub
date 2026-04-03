from __future__ import annotations
from typing import List

"""Segment router — CRUD with conditions."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.segment import Segment, SegmentCondition
from app.models.targeting import Comparator
from app.schemas.schemas import SegmentCreate, SegmentUpdate, SegmentOut
from app.services.auth import get_current_user
from app.services.audit import get_org_id_for_product, record_audit
from app.services.authz import require_product_member, require_product_permission

router = APIRouter(prefix="/api/v1/products/{product_id}/segments", tags=["Segments"])


@router.get("", response_model=List[SegmentOut])
async def list_segments(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(Segment)
        .options(selectinload(Segment.conditions))
        .where(Segment.product_id == product_id)
    )
    return result.scalars().all()


@router.post("", response_model=SegmentOut, status_code=status.HTTP_201_CREATED)
async def create_segment(
    product_id: str,
    body: SegmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageSegments")
    segment = Segment(
        product_id=product_id, name=body.name, description=body.description
    )
    db.add(segment)
    await db.flush()

    for cond_in in body.conditions:
        try:
            comp = Comparator(cond_in.comparator)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid comparator: {cond_in.comparator}"
            )
        cond = SegmentCondition(
            segment_id=segment.id,
            attribute=cond_in.attribute,
            comparator=comp,
            comparison_value=cond_in.comparison_value,
        )
        db.add(cond)

    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "segment",
            product_id=product_id,
            entity_id=segment.id,
            new_value={"name": segment.name, "description": segment.description},
        )
    return await _load_segment(segment.id, db)


@router.get("/{segment_id}", response_model=SegmentOut)
async def get_segment(
    product_id: str,
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    segment = await _load_segment(segment_id, db)
    if segment.product_id != product_id:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.patch("/{segment_id}", response_model=SegmentOut)
async def update_segment(
    product_id: str,
    segment_id: str,
    body: SegmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageSegments")
    segment = await _load_segment(segment_id, db)
    if segment.product_id != product_id:
        raise HTTPException(status_code=404, detail="Segment not found")
    old_value = {"name": segment.name, "description": segment.description}
    if body.name is not None:
        segment.name = body.name
    if body.description is not None:
        segment.description = body.description

    if body.conditions is not None:
        for old_cond in segment.conditions:
            await db.delete(old_cond)
        await db.flush()

        for cond_in in body.conditions:
            try:
                comp = Comparator(cond_in.comparator)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid comparator: {cond_in.comparator}"
                )
            cond = SegmentCondition(
                segment_id=segment.id,
                attribute=cond_in.attribute,
                comparator=comp,
                comparison_value=cond_in.comparison_value,
            )
            db.add(cond)

    await db.flush()
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "segment",
            product_id=product_id,
            entity_id=segment.id,
            old_value=old_value,
            new_value={"name": segment.name, "description": segment.description},
        )
    return await _load_segment(segment_id, db)


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    product_id: str,
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageSegments")
    result = await db.execute(
        select(Segment).where(
            Segment.id == segment_id, Segment.product_id == product_id
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "segment",
            product_id=product_id,
            entity_id=segment.id,
            old_value={"name": segment.name, "description": segment.description},
        )
    await db.delete(segment)


async def _load_segment(segment_id: str, db: AsyncSession) -> Segment:
    result = await db.execute(
        select(Segment)
        .options(selectinload(Segment.conditions))
        .where(Segment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment

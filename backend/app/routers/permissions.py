from __future__ import annotations

"""Permission group router — CRUD under a product."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.organization import OrgRole, OrganizationMember
from app.models.permission import PermissionGroup, ProductPermissionAssignment
from app.models.user import User
from app.schemas.schemas import ProductMemberAccessOut, ProductMemberPermissionUpdate
from app.services.auth import get_current_user
from app.services.audit import get_org_id_for_product, record_audit
from app.services.authz import require_product_admin, require_product_member

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
    await require_product_admin(db, product_id, current_user)
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
    await require_product_admin(db, product_id, current_user)
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
    await require_product_admin(db, product_id, current_user)
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


@router.get("/access", response_model=List[ProductMemberAccessOut])
async def list_product_member_access(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await require_product_member(db, product_id, current_user)

    member_result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(OrganizationMember.organization_id == product.organization_id)
    )
    members = member_result.scalars().all()
    member_ids = [member.id for member in members]

    assignments_by_member_id: dict[str, ProductPermissionAssignment] = {}
    if member_ids:
        assignment_result = await db.execute(
            select(ProductPermissionAssignment)
            .options(selectinload(ProductPermissionAssignment.permission_group))
            .where(
                ProductPermissionAssignment.product_id == product_id,
                ProductPermissionAssignment.organization_member_id.in_(member_ids),
            )
        )
        assignments_by_member_id = {
            assignment.organization_member_id: assignment
            for assignment in assignment_result.scalars().all()
        }

    members.sort(
        key=lambda member: (
            member.role != OrgRole.ADMIN,
            (member.user.email if member.user else "").lower(),
        )
    )

    return [
        _serialize_member_access(member, assignments_by_member_id.get(member.id))
        for member in members
    ]


@router.put("/access/{member_id}", response_model=ProductMemberAccessOut)
async def update_product_member_access(
    product_id: str,
    member_id: str,
    body: ProductMemberPermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await require_product_admin(db, product_id, current_user)
    member = await _get_product_org_member(db, product.organization_id, member_id)
    existing_assignment = await _get_permission_assignment(db, product_id, member.id)

    if member.role == OrgRole.ADMIN and body.permission_group_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Organization admins already have full product access",
        )

    old_value = _serialize_assignment_audit(existing_assignment)
    assignment: ProductPermissionAssignment | None = existing_assignment

    if body.permission_group_id is None:
        if existing_assignment is not None:
            await db.delete(existing_assignment)
            assignment = None
    else:
        group = await _get_permission_group(db, product_id, body.permission_group_id)
        if existing_assignment is None:
            assignment = ProductPermissionAssignment(
                product_id=product_id,
                organization_member_id=member.id,
                permission_group_id=group.id,
            )
            db.add(assignment)
        else:
            assignment.permission_group_id = group.id
        await db.flush()
        assignment = await _get_permission_assignment(db, product_id, member.id)

    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "permission_assignment",
            entity_id=member.id,
            old_value=old_value,
            new_value=_serialize_assignment_audit(assignment),
        )

    return _serialize_member_access(member, assignment)


async def _get_permission_group(
    db: AsyncSession,
    product_id: str,
    group_id: str,
) -> PermissionGroup:
    result = await db.execute(
        select(PermissionGroup).where(
            PermissionGroup.id == group_id,
            PermissionGroup.product_id == product_id,
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Permission group not found")
    return group


async def _get_product_org_member(
    db: AsyncSession,
    organization_id: str,
    member_id: str,
) -> OrganizationMember:
    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.id == member_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Organization member not found")
    return member


async def _get_permission_assignment(
    db: AsyncSession,
    product_id: str,
    member_id: str,
) -> ProductPermissionAssignment | None:
    result = await db.execute(
        select(ProductPermissionAssignment)
        .options(selectinload(ProductPermissionAssignment.permission_group))
        .where(
            ProductPermissionAssignment.product_id == product_id,
            ProductPermissionAssignment.organization_member_id == member_id,
        )
    )
    return result.scalar_one_or_none()


def _serialize_member_access(
    member: OrganizationMember,
    assignment: ProductPermissionAssignment | None,
) -> ProductMemberAccessOut:
    return ProductMemberAccessOut(
        member_id=member.id,
        user_id=member.user_id,
        role=member.role.value if isinstance(member.role, OrgRole) else str(member.role),
        user=member.user,
        permission_group_id=assignment.permission_group_id if assignment else None,
        permission_group_name=(
            assignment.permission_group.name
            if assignment and assignment.permission_group
            else None
        ),
    )


def _serialize_assignment_audit(
    assignment: ProductPermissionAssignment | None,
) -> dict | None:
    if assignment is None:
        return None
    return {
        "permission_group_id": assignment.permission_group_id,
        "permission_group_name": (
            assignment.permission_group.name
            if assignment.permission_group is not None
            else None
        ),
    }

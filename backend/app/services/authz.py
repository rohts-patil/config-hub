from __future__ import annotations

"""Authorization helpers for organization-scoped resources."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.config import Config
from app.models.environment import Environment
from app.models.organization import OrgRole, Organization, OrganizationMember
from app.models.permission import PermissionGroup, ProductPermissionAssignment
from app.models.product import Product
from app.models.user import User

PermissionKey = str


async def require_org_member(
    db: AsyncSession,
    org_id: str,
    user: User,
) -> Organization:
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    membership = await get_org_membership(db, org_id, user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    return org


async def get_org_membership(
    db: AsyncSession,
    org_id: str,
    user_id: str,
) -> OrganizationMember | None:
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return member_result.scalar_one_or_none()


async def require_org_admin(
    db: AsyncSession,
    org_id: str,
    user: User,
) -> Organization:
    org = await require_org_member(db, org_id, user)
    membership = await get_org_membership(db, org_id, user.id)
    if membership is None or membership.role != OrgRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only organization admins can perform this action"
        )
    return org


async def require_product_member(
    db: AsyncSession,
    product_id: str,
    user: User,
) -> Product:
    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await require_org_member(db, product.organization_id, user)
    return product


async def require_product_admin(
    db: AsyncSession,
    product_id: str,
    user: User,
) -> Product:
    product = await require_product_member(db, product_id, user)
    membership = await get_org_membership(db, product.organization_id, user.id)
    if membership is None or membership.role != OrgRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only organization admins can perform this action"
        )
    return product


async def _get_product_permission_assignment(
    db: AsyncSession,
    product_id: str,
    organization_member_id: str,
) -> ProductPermissionAssignment | None:
    result = await db.execute(
        select(ProductPermissionAssignment)
        .options(selectinload(ProductPermissionAssignment.permission_group))
        .where(
            ProductPermissionAssignment.product_id == product_id,
            ProductPermissionAssignment.organization_member_id == organization_member_id,
        )
    )
    return result.scalar_one_or_none()


async def require_product_permission(
    db: AsyncSession,
    product_id: str,
    user: User,
    permission_key: PermissionKey,
) -> Product:
    product = await require_product_member(db, product_id, user)
    membership = await get_org_membership(db, product.organization_id, user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    if membership.role == OrgRole.ADMIN:
        return product

    groups_result = await db.execute(
        select(PermissionGroup.id).where(PermissionGroup.product_id == product_id)
    )
    if groups_result.scalars().first() is None:
        return product

    assignment = await _get_product_permission_assignment(db, product_id, membership.id)
    allowed = bool(
        assignment
        and assignment.permission_group
        and assignment.permission_group.permissions.get(permission_key)
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this action for this product",
        )
    return product


async def require_config_member(
    db: AsyncSession,
    config_id: str,
    user: User,
    *,
    product_id: str | None = None,
) -> Config:
    config_result = await db.execute(select(Config).where(Config.id == config_id))
    config = config_result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    if product_id is not None and config.product_id != product_id:
        raise HTTPException(status_code=404, detail="Config not found")

    await require_product_member(db, config.product_id, user)
    return config


async def require_config_permission(
    db: AsyncSession,
    config_id: str,
    user: User,
    permission_key: PermissionKey,
    *,
    product_id: str | None = None,
) -> Config:
    config = await require_config_member(db, config_id, user, product_id=product_id)
    await require_product_permission(db, config.product_id, user, permission_key)
    return config


async def require_environment_member(
    db: AsyncSession,
    env_id: str,
    user: User,
    *,
    product_id: str | None = None,
) -> Environment:
    env_result = await db.execute(select(Environment).where(Environment.id == env_id))
    env = env_result.scalar_one_or_none()
    if env is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    if product_id is not None and env.product_id != product_id:
        raise HTTPException(status_code=404, detail="Environment not found")

    await require_product_member(db, env.product_id, user)
    return env


async def require_environment_permission(
    db: AsyncSession,
    env_id: str,
    user: User,
    permission_key: PermissionKey,
    *,
    product_id: str | None = None,
) -> Environment:
    env = await require_environment_member(db, env_id, user, product_id=product_id)
    await require_product_permission(db, env.product_id, user, permission_key)
    return env


async def get_org_product_ids_with_permission(
    db: AsyncSession,
    org_id: str,
    user: User,
    permission_key: PermissionKey,
) -> set[str] | None:
    await require_org_member(db, org_id, user)
    membership = await get_org_membership(db, org_id, user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    if membership.role == OrgRole.ADMIN:
        return None

    products_result = await db.execute(
        select(Product.id).where(Product.organization_id == org_id)
    )
    org_product_ids = set(products_result.scalars().all())
    if not org_product_ids:
        return set()

    groups_result = await db.execute(
        select(PermissionGroup).where(PermissionGroup.product_id.in_(org_product_ids))
    )
    permission_groups = groups_result.scalars().all()
    grouped_product_ids = {group.product_id for group in permission_groups}

    if not grouped_product_ids:
        return None

    accessible_product_ids = org_product_ids - grouped_product_ids

    assignment_result = await db.execute(
        select(ProductPermissionAssignment)
        .options(selectinload(ProductPermissionAssignment.permission_group))
        .where(
            ProductPermissionAssignment.organization_member_id == membership.id,
            ProductPermissionAssignment.product_id.in_(org_product_ids),
        )
    )
    for assignment in assignment_result.scalars().all():
        if (
            assignment.permission_group
            and assignment.permission_group.permissions.get(permission_key)
        ):
            accessible_product_ids.add(assignment.product_id)

    return accessible_product_ids

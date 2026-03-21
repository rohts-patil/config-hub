from __future__ import annotations

"""Authorization helpers for organization-scoped resources."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.models.environment import Environment
from app.models.organization import Organization, OrganizationMember
from app.models.product import Product
from app.models.user import User


async def require_org_member(
    db: AsyncSession,
    org_id: str,
    user: User,
) -> Organization:
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if member_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

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


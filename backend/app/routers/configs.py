from __future__ import annotations
from typing import List, Optional

"""Config and Environment routers — CRUD under a product."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.config import Config
from app.models.environment import Environment
from app.models.permission import SDKKey
from app.schemas.schemas import (
    ConfigCreate,
    ConfigUpdate,
    ConfigOut,
    EnvironmentCreate,
    EnvironmentUpdate,
    EnvironmentOut,
    SDKKeyOut,
)
from app.services.auth import get_current_user
from app.services.audit import record_audit, get_org_id_for_product
from app.services.authz import require_config_member, require_product_member

# ── Config ────────────────────────────────────────────────────────────────────

config_router = APIRouter(
    prefix="/api/v1/products/{product_id}/configs", tags=["Configs"]
)


@config_router.get("", response_model=List[ConfigOut])
async def list_configs(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(Config).where(Config.product_id == product_id).order_by(Config.order)
    )
    return result.scalars().all()


@config_router.post("", response_model=ConfigOut, status_code=status.HTTP_201_CREATED)
async def create_config(
    product_id: str,
    body: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    config = Config(product_id=product_id, name=body.name)
    db.add(config)
    await db.flush()

    # Auto-generate SDK keys for every existing environment
    envs = await db.execute(
        select(Environment).where(Environment.product_id == product_id)
    )
    for env in envs.scalars().all():
        sdk_key = SDKKey(
            config_id=config.id,
            environment_id=env.id,
            key=f"{config.id[:8]}/{env.id[:8]}/{secrets.token_urlsafe(22)}",
        )
        db.add(sdk_key)
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db, org_id, current_user.id, "created", "config",
            entity_id=config.id, new_value={"name": config.name},
        )

    return config


@config_router.get("/{config_id}", response_model=ConfigOut)
async def get_config(
    product_id: str,
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await require_config_member(db, config_id, current_user, product_id=product_id)


@config_router.patch("/{config_id}", response_model=ConfigOut)
async def update_config(
    product_id: str,
    config_id: str,
    body: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await require_config_member(db, config_id, current_user, product_id=product_id)
    old_value = {"name": config.name, "order": config.order}
    if body.name is not None:
        config.name = body.name
    if body.order is not None:
        config.order = body.order
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db, org_id, current_user.id, "updated", "config",
            entity_id=config.id, old_value=old_value,
            new_value={"name": config.name, "order": config.order},
        )

    return config


@config_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    product_id: str,
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await require_config_member(db, config_id, current_user, product_id=product_id)

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db, org_id, current_user.id, "deleted", "config",
            entity_id=config.id, old_value={"name": config.name},
        )

    await db.delete(config)


# ── Environment ───────────────────────────────────────────────────────────────

env_router = APIRouter(
    prefix="/api/v1/products/{product_id}/environments", tags=["Environments"]
)


@env_router.get("", response_model=List[EnvironmentOut])
async def list_environments(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(Environment)
        .where(Environment.product_id == product_id)
        .order_by(Environment.order)
    )
    return result.scalars().all()


@env_router.post("", response_model=EnvironmentOut, status_code=status.HTTP_201_CREATED)
async def create_environment(
    product_id: str,
    body: EnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    env = Environment(product_id=product_id, name=body.name, color=body.color)
    db.add(env)
    await db.flush()

    # Auto-generate SDK keys for every existing config
    configs = await db.execute(select(Config).where(Config.product_id == product_id))
    for cfg in configs.scalars().all():
        sdk_key = SDKKey(
            config_id=cfg.id,
            environment_id=env.id,
            key=f"{cfg.id[:8]}/{env.id[:8]}/{secrets.token_urlsafe(22)}",
        )
        db.add(sdk_key)
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "environment",
            entity_id=env.id,
            new_value={"name": env.name, "color": env.color},
        )
    return env


@env_router.patch("/{env_id}", response_model=EnvironmentOut)
async def update_environment(
    product_id: str,
    env_id: str,
    body: EnvironmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(Environment).where(
            Environment.id == env_id, Environment.product_id == product_id
        )
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    old_value = {"name": env.name, "color": env.color, "order": env.order}
    if body.name is not None:
        env.name = body.name
    if body.color is not None:
        env.color = body.color
    if body.order is not None:
        env.order = body.order
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "environment",
            entity_id=env.id,
            old_value=old_value,
            new_value={"name": env.name, "color": env.color, "order": env.order},
        )
    return env


@env_router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    product_id: str,
    env_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    result = await db.execute(
        select(Environment).where(
            Environment.id == env_id, Environment.product_id == product_id
        )
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "environment",
            entity_id=env.id,
            old_value={"name": env.name, "color": env.color},
        )
    await db.delete(env)


# ── SDK Keys ──────────────────────────────────────────────────────────────────

sdk_key_router = APIRouter(
    prefix="/api/v1/products/{product_id}/sdk-keys", tags=["SDK Keys"]
)


@sdk_key_router.get("", response_model=List[SDKKeyOut])
async def list_sdk_keys(
    product_id: str,
    config_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_member(db, product_id, current_user)
    query = select(SDKKey).join(Config).where(Config.product_id == product_id)
    if config_id:
        query = query.where(SDKKey.config_id == config_id)
    result = await db.execute(query.order_by(SDKKey.created_at.desc()))
    return result.scalars().all()

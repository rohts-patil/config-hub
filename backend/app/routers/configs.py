from __future__ import annotations

"""Config and Environment routers — CRUD under a product."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.config import Config
from app.models.environment import Environment
from app.models.permission import SDKKey
from app.schemas.schemas import (
    ConfigCreate, ConfigUpdate, ConfigOut,
    EnvironmentCreate, EnvironmentUpdate, EnvironmentOut,
    SDKKeyOut,
)
from app.services.auth import get_current_user

# ── Config ────────────────────────────────────────────────────────────────────

config_router = APIRouter(prefix="/api/v1/products/{product_id}/configs", tags=["Configs"])


@config_router.get("", response_model=list[ConfigOut])
async def list_configs(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Config).where(Config.product_id == product_id).order_by(Config.order))
    return result.scalars().all()


@config_router.post("", response_model=ConfigOut, status_code=status.HTTP_201_CREATED)
async def create_config(
    product_id: str,
    body: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = Config(product_id=product_id, name=body.name)
    db.add(config)
    await db.flush()

    # Auto-generate SDK keys for every existing environment
    envs = await db.execute(select(Environment).where(Environment.product_id == product_id))
    for env in envs.scalars().all():
        sdk_key = SDKKey(
            config_id=config.id,
            environment_id=env.id,
            key=f"{config.id[:8]}/{env.id[:8]}/{secrets.token_urlsafe(22)}",
        )
        db.add(sdk_key)
    await db.flush()
    return config


@config_router.patch("/{config_id}", response_model=ConfigOut)
async def update_config(
    product_id: str,
    config_id: str,
    body: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Config).where(Config.id == config_id, Config.product_id == product_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    if body.name is not None:
        config.name = body.name
    if body.order is not None:
        config.order = body.order
    await db.flush()
    return config


@config_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    product_id: str,
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Config).where(Config.id == config_id, Config.product_id == product_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.delete(config)


# ── Environment ───────────────────────────────────────────────────────────────

env_router = APIRouter(prefix="/api/v1/products/{product_id}/environments", tags=["Environments"])


@env_router.get("", response_model=list[EnvironmentOut])
async def list_environments(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Environment).where(Environment.product_id == product_id).order_by(Environment.order)
    )
    return result.scalars().all()


@env_router.post("", response_model=EnvironmentOut, status_code=status.HTTP_201_CREATED)
async def create_environment(
    product_id: str,
    body: EnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    return env


@env_router.patch("/{env_id}", response_model=EnvironmentOut)
async def update_environment(
    product_id: str,
    env_id: str,
    body: EnvironmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Environment).where(Environment.id == env_id, Environment.product_id == product_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    if body.name is not None:
        env.name = body.name
    if body.color is not None:
        env.color = body.color
    if body.order is not None:
        env.order = body.order
    await db.flush()
    return env


@env_router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    product_id: str,
    env_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Environment).where(Environment.id == env_id, Environment.product_id == product_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    await db.delete(env)


# ── SDK Keys ──────────────────────────────────────────────────────────────────

sdk_key_router = APIRouter(prefix="/api/v1/products/{product_id}/sdk-keys", tags=["SDK Keys"])


@sdk_key_router.get("", response_model=list[SDKKeyOut])
async def list_sdk_keys(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SDKKey)
        .join(Config)
        .where(Config.product_id == product_id)
    )
    return result.scalars().all()

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
    SDKKeyCreate,
    SDKKeySecretOut,
    SDKKeySummaryOut,
)
from app.services.auth import get_current_user
from app.services.audit import record_audit, get_org_id_for_product
from app.services.authz import (
    require_config_member,
    require_config_permission,
    require_environment_member,
    require_environment_permission,
    require_product_member,
    require_product_permission,
)

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
    await require_product_permission(db, product_id, current_user, "canManageFlags")
    config = Config(product_id=product_id, name=body.name)
    db.add(config)
    await db.flush()

    # Auto-generate SDK keys for every existing environment
    envs = await db.execute(
        select(Environment).where(Environment.product_id == product_id)
    )
    for env in envs.scalars().all():
        sdk_key = _build_sdk_key(config.id, env.id)
        db.add(sdk_key)
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "config",
            entity_id=config.id,
            new_value={"name": config.name},
        )

    return config


@config_router.get("/{config_id}", response_model=ConfigOut)
async def get_config(
    product_id: str,
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await require_config_member(
        db, config_id, current_user, product_id=product_id
    )


@config_router.patch("/{config_id}", response_model=ConfigOut)
async def update_config(
    product_id: str,
    config_id: str,
    body: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await require_config_permission(
        db,
        config_id,
        current_user,
        "canManageFlags",
        product_id=product_id,
    )
    old_value = {"name": config.name, "order": config.order}
    if body.name is not None:
        config.name = body.name
    if body.order is not None:
        config.order = body.order
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "config",
            entity_id=config.id,
            old_value=old_value,
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
    config = await require_config_permission(
        db,
        config_id,
        current_user,
        "canManageFlags",
        product_id=product_id,
    )

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "config",
            entity_id=config.id,
            old_value={"name": config.name},
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
    await require_product_permission(
        db, product_id, current_user, "canManageEnvironments"
    )
    env = Environment(product_id=product_id, name=body.name, color=body.color)
    db.add(env)
    await db.flush()

    # Auto-generate SDK keys for every existing config
    configs = await db.execute(select(Config).where(Config.product_id == product_id))
    for cfg in configs.scalars().all():
        sdk_key = _build_sdk_key(cfg.id, env.id)
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
    await require_environment_permission(
        db,
        env_id,
        current_user,
        "canManageEnvironments",
        product_id=product_id,
    )
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
    await require_environment_permission(
        db,
        env_id,
        current_user,
        "canManageEnvironments",
        product_id=product_id,
    )
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


@sdk_key_router.get("", response_model=List[SDKKeySummaryOut])
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
    return [_sdk_key_summary(key) for key in result.scalars().all()]


@sdk_key_router.post(
    "", response_model=SDKKeySecretOut, status_code=status.HTTP_201_CREATED
)
async def create_sdk_key(
    product_id: str,
    body: SDKKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageSdkKeys")
    config = await require_config_member(
        db,
        body.config_id,
        current_user,
        product_id=product_id,
    )
    environment = await require_environment_member(
        db,
        body.environment_id,
        current_user,
        product_id=product_id,
    )

    sdk_key = _build_sdk_key(config.id, environment.id)
    db.add(sdk_key)
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "sdk_key",
            entity_id=sdk_key.id,
            new_value={
                "config_name": config.name,
                "environment_name": environment.name,
                "key_prefix": sdk_key.key[:16],
            },
        )

    return _sdk_key_secret(sdk_key)


@sdk_key_router.post("/{sdk_key_id}/revoke", response_model=SDKKeySummaryOut)
async def revoke_sdk_key(
    product_id: str,
    sdk_key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageSdkKeys")
    sdk_key = await _load_sdk_key_for_product(db, product_id, sdk_key_id)
    if sdk_key.revoked:
        return _sdk_key_summary(sdk_key)

    sdk_key.revoked = True
    await db.flush()

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "sdk_key",
            entity_id=sdk_key.id,
            new_value={"status": "revoked"},
        )

    return _sdk_key_summary(sdk_key)


@sdk_key_router.delete("/{sdk_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sdk_key(
    product_id: str,
    sdk_key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_product_permission(db, product_id, current_user, "canManageSdkKeys")
    sdk_key = await _load_sdk_key_for_product(db, product_id, sdk_key_id)

    org_id = await get_org_id_for_product(db, product_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "sdk_key",
            entity_id=sdk_key.id,
            old_value={"status": "revoked" if sdk_key.revoked else "active"},
        )

    await db.delete(sdk_key)


def _build_sdk_key(config_id: str, environment_id: str) -> SDKKey:
    return SDKKey(
        config_id=config_id,
        environment_id=environment_id,
        key=f"{config_id[:8]}/{environment_id[:8]}/{secrets.token_urlsafe(22)}",
    )


async def _load_sdk_key_for_product(
    db: AsyncSession,
    product_id: str,
    sdk_key_id: str,
) -> SDKKey:
    result = await db.execute(
        select(SDKKey)
        .join(Config)
        .where(SDKKey.id == sdk_key_id, Config.product_id == product_id)
    )
    sdk_key = result.scalar_one_or_none()
    if not sdk_key:
        raise HTTPException(status_code=404, detail="SDK key not found")
    return sdk_key


def _sdk_key_summary(sdk_key: SDKKey) -> dict:
    return {
        "id": sdk_key.id,
        "config_id": sdk_key.config_id,
        "environment_id": sdk_key.environment_id,
        "masked_key": "********************",
        "revoked": sdk_key.revoked,
        "created_at": sdk_key.created_at,
    }


def _sdk_key_secret(sdk_key: SDKKey) -> dict:
    return {
        **_sdk_key_summary(sdk_key),
        "key": sdk_key.key,
    }

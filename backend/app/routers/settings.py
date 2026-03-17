from __future__ import annotations

"""Setting (feature flag) router — CRUD + value/targeting-rule management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.setting import Setting, SettingValue, SettingType
from app.models.targeting import TargetingRule, Condition, PercentageOption, Comparator, ConditionType
from app.models.environment import Environment
from app.schemas.schemas import (
    SettingCreate, SettingUpdate, SettingOut,
    SettingValueUpdate, SettingValueOut,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/v1/configs/{config_id}/settings", tags=["Settings"])


@router.get("", response_model=list[SettingOut])
async def list_settings(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Setting).where(Setting.config_id == config_id).order_by(Setting.order)
    )
    return result.scalars().all()


@router.post("", response_model=SettingOut, status_code=status.HTTP_201_CREATED)
async def create_setting(
    config_id: str,
    body: SettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate setting type
    try:
        s_type = SettingType(body.setting_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid setting type: {body.setting_type}")

    # Check key uniqueness within config
    existing = await db.execute(
        select(Setting).where(Setting.config_id == config_id, Setting.key == body.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Setting key '{body.key}' already exists in this config")

    setting = Setting(
        config_id=config_id,
        key=body.key,
        name=body.name,
        hint=body.hint,
        setting_type=s_type,
    )
    db.add(setting)
    await db.flush()

    # Auto-create SettingValues for all environments in the same product
    from app.models.config import Config
    cfg = await db.execute(select(Config).where(Config.id == config_id))
    config_obj = cfg.scalar_one_or_none()
    if config_obj:
        envs = await db.execute(
            select(Environment).where(Environment.product_id == config_obj.product_id)
        )
        default = _default_for_type(s_type)
        for env in envs.scalars().all():
            sv = SettingValue(
                setting_id=setting.id,
                environment_id=env.id,
                default_value={"v": default},
            )
            db.add(sv)
    await db.flush()
    return setting


@router.get("/{setting_id}", response_model=SettingOut)
async def get_setting(
    config_id: str,
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Setting).where(Setting.id == setting_id, Setting.config_id == config_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.patch("/{setting_id}", response_model=SettingOut)
async def update_setting(
    config_id: str,
    setting_id: str,
    body: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Setting).where(Setting.id == setting_id, Setting.config_id == config_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    if body.name is not None:
        setting.name = body.name
    if body.hint is not None:
        setting.hint = body.hint
    if body.order is not None:
        setting.order = body.order
    await db.flush()
    return setting


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    config_id: str,
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Setting).where(Setting.id == setting_id, Setting.config_id == config_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(setting)


# ── Setting Value + Targeting Rules per Environment ───────────────────────────

@router.get("/{setting_id}/values/{env_id}", response_model=SettingValueOut)
async def get_setting_value(
    config_id: str,
    setting_id: str,
    env_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sv = await _load_setting_value(setting_id, env_id, db)
    return sv


@router.put("/{setting_id}/values/{env_id}", response_model=SettingValueOut)
async def update_setting_value(
    config_id: str,
    setting_id: str,
    env_id: str,
    body: SettingValueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sv = await _load_setting_value(setting_id, env_id, db)

    # Update default value
    sv.default_value = body.default_value

    # Replace targeting rules — delete old, insert new
    for old_rule in sv.targeting_rules:
        await db.delete(old_rule)
    await db.flush()

    for i, rule_in in enumerate(body.targeting_rules):
        rule = TargetingRule(
            setting_value_id=sv.id,
            served_value=rule_in.served_value,
            order=rule_in.order if rule_in.order else i,
        )
        db.add(rule)
        await db.flush()

        for cond_in in rule_in.conditions:
            try:
                comp = Comparator(cond_in.comparator)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid comparator: {cond_in.comparator}")
            try:
                ctype = ConditionType(cond_in.condition_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid condition type: {cond_in.condition_type}")

            condition = Condition(
                targeting_rule_id=rule.id,
                condition_type=ctype,
                attribute=cond_in.attribute,
                comparator=comp,
                comparison_value=cond_in.comparison_value,
                segment_id=cond_in.segment_id,
                prerequisite_setting_id=cond_in.prerequisite_setting_id,
            )
            db.add(condition)

    # Replace percentage options
    for old_pct in sv.percentage_options:
        await db.delete(old_pct)
    await db.flush()

    for i, pct_in in enumerate(body.percentage_options):
        pct = PercentageOption(
            setting_value_id=sv.id,
            percentage=pct_in.percentage,
            value=pct_in.value,
            order=pct_in.order if pct_in.order else i,
        )
        db.add(pct)

    await db.flush()

    # Reload
    return await _load_setting_value(setting_id, env_id, db)


async def _load_setting_value(setting_id: str, env_id: str, db: AsyncSession) -> SettingValue:
    result = await db.execute(
        select(SettingValue)
        .options(
            selectinload(SettingValue.targeting_rules).selectinload(TargetingRule.conditions),
            selectinload(SettingValue.percentage_options),
        )
        .where(SettingValue.setting_id == setting_id, SettingValue.environment_id == env_id)
    )
    sv = result.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Setting value not found for this environment")
    return sv


def _default_for_type(setting_type: SettingType):
    if setting_type == SettingType.BOOLEAN:
        return False
    elif setting_type == SettingType.STRING:
        return ""
    elif setting_type == SettingType.INT:
        return 0
    elif setting_type == SettingType.DOUBLE:
        return 0.0
    return None

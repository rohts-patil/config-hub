from __future__ import annotations
from typing import List

"""Setting (feature flag) router — CRUD + value/targeting-rule management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.setting import Setting, SettingValue, SettingType
from app.models.targeting import (
    TargetingRule,
    Condition,
    PercentageOption,
    Comparator,
    ConditionType,
)
from app.models.environment import Environment
from app.schemas.schemas import (
    ConditionIn,
    PercentageOptionIn,
    SettingCreate,
    SettingUpdate,
    SettingOut,
    SettingValueUpdate,
    SettingValueOut,
    TargetingRuleIn,
)
from app.services.auth import get_current_user
from app.services.audit import get_org_id_for_config, get_product_id_for_config, record_audit
from app.services.authz import (
    require_config_member,
    require_config_permission,
    require_environment_member,
)
from app.services.webhook import dispatch_webhooks

router = APIRouter(prefix="/api/v1/configs/{config_id}/settings", tags=["Settings"])


@router.get("", response_model=List[SettingOut])
async def list_settings(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_config_member(db, config_id, current_user)
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
    config_obj = await require_config_permission(
        db, config_id, current_user, "canManageFlags"
    )
    # Validate setting type
    try:
        s_type = SettingType(body.setting_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid setting type: {body.setting_type}"
        )

    # Check key uniqueness within config
    existing = await db.execute(
        select(Setting).where(Setting.config_id == config_id, Setting.key == body.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Setting key '{body.key}' already exists in this config",
        )

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

    # Audit log
    org_id = await get_org_id_for_config(db, config_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "created",
            "setting",
            product_id=config_obj.product_id,
            entity_id=setting.id,
            new_value={"key": setting.key, "name": setting.name, "type": s_type.value},
        )

    return setting


@router.get("/{setting_id}", response_model=SettingOut)
async def get_setting(
    config_id: str,
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_config_member(db, config_id, current_user)
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
    setting = await _load_setting(config_id, setting_id, db)
    await require_config_permission(db, config_id, current_user, "canManageFlags")

    old_value = {"name": setting.name, "hint": setting.hint, "order": setting.order}
    if body.name is not None:
        setting.name = body.name
    if body.hint is not None:
        setting.hint = body.hint
    if body.order is not None:
        setting.order = body.order
    await db.flush()

    org_id = await get_org_id_for_config(db, config_id)
    product_id = await get_product_id_for_config(db, config_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "setting",
            product_id=product_id,
            entity_id=setting.id,
            old_value=old_value,
            new_value={
                "name": setting.name,
                "hint": setting.hint,
                "order": setting.order,
            },
        )

    return setting


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    config_id: str,
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = await _load_setting(config_id, setting_id, db)
    await require_config_permission(db, config_id, current_user, "canManageFlags")

    org_id = await get_org_id_for_config(db, config_id)
    product_id = await get_product_id_for_config(db, config_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "deleted",
            "setting",
            product_id=product_id,
            entity_id=setting.id,
            old_value={"key": setting.key, "name": setting.name},
        )

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
    config_obj = await require_config_member(db, config_id, current_user)
    await require_environment_member(
        db,
        env_id,
        current_user,
        product_id=config_obj.product_id,
    )
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
    config_obj = await require_config_permission(
        db, config_id, current_user, "canManageFlags"
    )
    environment = await require_environment_member(
        db,
        env_id,
        current_user,
        product_id=config_obj.product_id,
    )
    setting = await _load_setting(config_id, setting_id, db)
    sv = await _load_setting_value(setting_id, env_id, db)

    old_state = _serialize_setting_value_for_audit(sv, setting, environment)

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
                raise HTTPException(
                    status_code=400, detail=f"Invalid comparator: {cond_in.comparator}"
                )
            try:
                ctype = ConditionType(cond_in.condition_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid condition type: {cond_in.condition_type}",
                )

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
    new_state = _serialize_setting_value_update_for_audit(body, setting, environment)

    # Audit log + webhooks
    org_id = await get_org_id_for_config(db, config_id)
    if org_id:
        await record_audit(
            db,
            org_id,
            current_user.id,
            "updated",
            "setting_value",
            product_id=config_obj.product_id,
            entity_id=sv.id,
            old_value=old_state,
            new_value=new_state,
        )

    # Resolve product_id for webhooks
    await dispatch_webhooks(
        db,
        config_obj.product_id,
        "setting.value_updated",
        {"setting_id": setting_id, "environment_id": env_id},
        config_id=config_id,
        environment_id=env_id,
    )

    # Reload
    return await _load_setting_value(setting_id, env_id, db)


async def _load_setting_value(
    setting_id: str, env_id: str, db: AsyncSession
) -> SettingValue:
    result = await db.execute(
        select(SettingValue)
        .options(
            selectinload(SettingValue.targeting_rules).selectinload(
                TargetingRule.conditions
            ),
            selectinload(SettingValue.percentage_options),
        )
        .where(
            SettingValue.setting_id == setting_id, SettingValue.environment_id == env_id
        )
    )
    sv = result.scalar_one_or_none()
    if not sv:
        raise HTTPException(
            status_code=404, detail="Setting value not found for this environment"
        )
    return sv


async def _load_setting(config_id: str, setting_id: str, db: AsyncSession) -> Setting:
    result = await db.execute(
        select(Setting).where(Setting.id == setting_id, Setting.config_id == config_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


def _serialize_setting_value_for_audit(
    setting_value: SettingValue,
    setting: Setting,
    environment: Environment,
) -> dict:
    return {
        "setting_key": setting.key,
        "setting_name": setting.name,
        "environment_name": environment.name,
        "default_value": setting_value.default_value,
        "targeting_rules": [
            _serialize_targeting_rule_for_audit(rule)
            for rule in sorted(
                setting_value.targeting_rules, key=lambda item: item.order
            )
        ],
        "percentage_options": [
            _serialize_percentage_option_for_audit(option)
            for option in sorted(
                setting_value.percentage_options, key=lambda item: item.order
            )
        ],
    }


def _serialize_setting_value_update_for_audit(
    body: SettingValueUpdate,
    setting: Setting,
    environment: Environment,
) -> dict:
    return {
        "setting_key": setting.key,
        "setting_name": setting.name,
        "environment_name": environment.name,
        "default_value": body.default_value,
        "targeting_rules": [
            _serialize_targeting_rule_input_for_audit(rule)
            for rule in sorted(body.targeting_rules, key=lambda item: item.order)
        ],
        "percentage_options": [
            _serialize_percentage_option_input_for_audit(option)
            for option in sorted(body.percentage_options, key=lambda item: item.order)
        ],
    }


def _serialize_targeting_rule_for_audit(rule: TargetingRule) -> dict:
    return {
        "served_value": rule.served_value,
        "conditions": [
            _serialize_condition_for_audit(condition)
            for condition in sorted(rule.conditions, key=lambda item: item.id)
        ],
        "order": rule.order,
    }


def _serialize_targeting_rule_input_for_audit(rule: TargetingRuleIn) -> dict:
    return {
        "served_value": rule.served_value,
        "conditions": [
            _serialize_condition_input_for_audit(condition)
            for condition in rule.conditions
        ],
        "order": rule.order,
    }


def _serialize_condition_for_audit(condition: Condition) -> dict:
    return {
        "condition_type": condition.condition_type.value,
        "attribute": condition.attribute,
        "comparator": condition.comparator.value,
        "comparison_value": condition.comparison_value,
        "segment_id": condition.segment_id,
        "prerequisite_setting_id": condition.prerequisite_setting_id,
    }


def _serialize_condition_input_for_audit(condition: ConditionIn) -> dict:
    return {
        "condition_type": condition.condition_type,
        "attribute": condition.attribute,
        "comparator": condition.comparator,
        "comparison_value": condition.comparison_value,
        "segment_id": condition.segment_id,
        "prerequisite_setting_id": condition.prerequisite_setting_id,
    }


def _serialize_percentage_option_for_audit(option: PercentageOption) -> dict:
    return {
        "percentage": option.percentage,
        "value": option.value,
        "order": option.order,
    }


def _serialize_percentage_option_input_for_audit(option: PercentageOptionIn) -> dict:
    return {
        "percentage": option.percentage,
        "value": option.value,
        "order": option.order,
    }


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

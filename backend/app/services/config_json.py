from __future__ import annotations

"""Config JSON generator for SDK consumption."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.config import Config
from app.models.setting import Setting, SettingValue
from app.models.targeting import TargetingRule, Condition, PercentageOption
from app.models.segment import Segment, SegmentCondition
from app.models.permission import SDKKey


async def generate_config_json(sdk_key_str: str, db: AsyncSession) -> dict | None:
    """Generate the config JSON blob that SDKs fetch and cache locally.

    Returns None if the SDK key is invalid or revoked.
    """
    # Look up SDK key
    result = await db.execute(
        select(SDKKey).where(
            SDKKey.key == sdk_key_str, SDKKey.revoked == False
        )  # noqa: E712
    )
    sdk_key = result.scalar_one_or_none()
    if not sdk_key:
        return None

    config_id = sdk_key.config_id
    environment_id = sdk_key.environment_id

    # Load config to get product_id for segments
    config_result = await db.execute(select(Config).where(Config.id == config_id))
    config_obj = config_result.scalar_one_or_none()
    if not config_obj:
        return None

    # Load all settings in this config
    settings_result = await db.execute(
        select(Setting).where(Setting.config_id == config_id).order_by(Setting.order)
    )
    settings_list = settings_result.scalars().all()

    settings_json = {}
    for setting in settings_list:
        # Load the setting value for this environment
        sv_result = await db.execute(
            select(SettingValue)
            .options(
                selectinload(SettingValue.targeting_rules).selectinload(
                    TargetingRule.conditions
                ),
                selectinload(SettingValue.percentage_options),
            )
            .where(
                SettingValue.setting_id == setting.id,
                SettingValue.environment_id == environment_id,
            )
        )
        sv = sv_result.scalar_one_or_none()

        setting_data: dict = {
            "type": (
                setting.setting_type.value
                if hasattr(setting.setting_type, "value")
                else setting.setting_type
            ),
            "value": (
                sv.default_value.get("v")
                if sv and sv.default_value
                else _type_default(setting.setting_type)
            ),
        }

        # Add targeting rules
        if sv and sv.targeting_rules:
            rules = sorted(sv.targeting_rules, key=lambda r: r.order)
            setting_data["targetingRules"] = [
                {
                    "conditions": [
                        {
                            "type": (
                                c.condition_type.value
                                if hasattr(c.condition_type, "value")
                                else c.condition_type
                            ),
                            "attribute": c.attribute,
                            "comparator": (
                                c.comparator.value
                                if hasattr(c.comparator, "value")
                                else c.comparator
                            ),
                            "comparisonValue": (
                                c.comparison_value.get("v")
                                if c.comparison_value
                                else None
                            ),
                            **({"segmentId": c.segment_id} if c.segment_id else {}),
                            **(
                                {"prerequisiteFlagKey": c.prerequisite_setting_id}
                                if c.prerequisite_setting_id
                                else {}
                            ),
                        }
                        for c in sorted(rule.conditions, key=lambda x: x.id)
                    ],
                    "value": rule.served_value.get("v") if rule.served_value else None,
                }
                for rule in rules
            ]

        # Add percentage options
        if sv and sv.percentage_options:
            pcts = sorted(sv.percentage_options, key=lambda p: p.order)
            setting_data["percentageOptions"] = [
                {
                    "percentage": p.percentage,
                    "value": p.value.get("v") if p.value else None,
                }
                for p in pcts
            ]

        settings_json[setting.key] = setting_data

    # Load segments for this product
    segments_result = await db.execute(
        select(Segment)
        .options(selectinload(Segment.conditions))
        .where(Segment.product_id == config_obj.product_id)
    )
    segments_list = segments_result.scalars().all()
    segments_json = [
        {
            "id": seg.id,
            "name": seg.name,
            "conditions": [
                {
                    "attribute": sc.attribute,
                    "comparator": (
                        sc.comparator.value
                        if hasattr(sc.comparator, "value")
                        else sc.comparator
                    ),
                    "comparisonValue": (
                        sc.comparison_value.get("v") if sc.comparison_value else None
                    ),
                }
                for sc in seg.conditions
            ],
        }
        for seg in segments_list
    ]

    return {
        "settings": settings_json,
        "segments": segments_json,
    }


def _type_default(setting_type) -> object:
    t = setting_type.value if hasattr(setting_type, "value") else setting_type
    if t == "boolean":
        return False
    elif t == "string":
        return ""
    elif t == "int":
        return 0
    elif t == "double":
        return 0.0
    return None

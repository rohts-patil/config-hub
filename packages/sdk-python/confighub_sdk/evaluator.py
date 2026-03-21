from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .types import Condition, ConfigJson, SegmentDefinition, SettingData, UserObject


def evaluate_flag(
    setting_key: str,
    setting: SettingData,
    user: Optional[UserObject] = None,
    segments: Optional[List[SegmentDefinition]] = None,
) -> Any:
    if segments is None:
        segments = []

    targeting_rules = setting.get("targetingRules", [])
    for rule in targeting_rules:
        conditions = rule.get("conditions", [])
        if conditions and _all_conditions_match(conditions, user, segments):
            return rule.get("value")

    percentage_options = setting.get("percentageOptions", [])
    identifier = (user or {}).get("identifier", "")
    if percentage_options and identifier:
        bucket = _get_percentage_bucket(setting_key, str(identifier))
        cumulative = 0
        for option in percentage_options:
            cumulative += int(option.get("percentage", 0))
            if bucket < cumulative:
                return option.get("value")

    return setting.get("value")


def evaluate_all_flags(
    config: ConfigJson,
    user: Optional[UserObject] = None,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    segments = config.get("segments", [])
    for key, setting in config.get("settings", {}).items():
        results[key] = evaluate_flag(key, setting, user, segments)
    return results


def _get_percentage_bucket(setting_key: str, user_id: str) -> int:
    value = f"{setting_key}{user_id}"
    hash_value = 2166136261
    for char in value:
        hash_value ^= ord(char)
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return hash_value % 100


def _all_conditions_match(
    conditions: Sequence[Condition],
    user: Optional[UserObject],
    segments: Sequence[SegmentDefinition],
) -> bool:
    return all(
        _condition_matches(condition, user, segments) for condition in conditions
    )


def _condition_matches(
    condition: Condition,
    user: Optional[UserObject],
    segments: Sequence[SegmentDefinition],
) -> bool:
    condition_type = condition.get("type", "user")

    if condition_type == "segment":
        segment_id = condition.get("segmentId")
        comparator = condition.get("comparator", "isOneOf")
        segment = next(
            (item for item in segments if item.get("id") == segment_id), None
        )
        if segment is None:
            return False
        matches = _all_conditions_match(segment.get("conditions", []), user, segments)
        if comparator in {"isOneOf", "equals"}:
            return matches
        if comparator in {"isNotOneOf", "notEquals"}:
            return not matches
        return False

    if condition_type == "flag":
        return True

    if not user:
        return False

    attribute = condition.get("attribute", "")
    user_value = user.get(attribute)
    if user_value is None:
        return False

    return _compare(
        condition.get("comparator", ""),
        user_value,
        condition.get("comparisonValue"),
    )


def _compare(comparator: str, user_value: Any, comparison_value: Any) -> bool:
    user_text = str(user_value)
    comparison_text = "" if comparison_value is None else str(comparison_value)

    if comparator == "equals":
        return user_text == comparison_text
    if comparator == "notEquals":
        return user_text != comparison_text
    if comparator == "contains":
        return comparison_text in user_text
    if comparator == "notContains":
        return comparison_text not in user_text
    if comparator == "startsWith":
        return user_text.startswith(comparison_text)
    if comparator == "notStartsWith":
        return not user_text.startswith(comparison_text)
    if comparator == "endsWith":
        return user_text.endswith(comparison_text)
    if comparator == "notEndsWith":
        return not user_text.endswith(comparison_text)

    if comparator == "isOneOf":
        values = [str(item) for item in _as_list(comparison_value, comparison_text)]
        return user_text in values
    if comparator == "isNotOneOf":
        values = [str(item) for item in _as_list(comparison_value, comparison_text)]
        return user_text not in values

    if comparator in {
        "numberEquals",
        "numberNotEquals",
        "numberLess",
        "numberLessOrEquals",
        "numberGreater",
        "numberGreaterOrEquals",
    }:
        try:
            numeric_user = float(user_value)
            numeric_comp = float(comparison_value)
        except (TypeError, ValueError):
            return False
        if comparator == "numberEquals":
            return numeric_user == numeric_comp
        if comparator == "numberNotEquals":
            return numeric_user != numeric_comp
        if comparator == "numberLess":
            return numeric_user < numeric_comp
        if comparator == "numberLessOrEquals":
            return numeric_user <= numeric_comp
        if comparator == "numberGreater":
            return numeric_user > numeric_comp
        return numeric_user >= numeric_comp

    if comparator in {
        "semverEquals",
        "semverNotEquals",
        "semverLess",
        "semverLessOrEquals",
        "semverGreater",
        "semverGreaterOrEquals",
    }:
        left = _parse_semver(user_text)
        right = _parse_semver(comparison_text)
        if left is None or right is None:
            return False
        cmp_result = _compare_semver(left, right)
        if comparator == "semverEquals":
            return cmp_result == 0
        if comparator == "semverNotEquals":
            return cmp_result != 0
        if comparator == "semverLess":
            return cmp_result < 0
        if comparator == "semverLessOrEquals":
            return cmp_result <= 0
        if comparator == "semverGreater":
            return cmp_result > 0
        return cmp_result >= 0

    if comparator in {"before", "after"}:
        left = _parse_datetime(user_text)
        right = _parse_datetime(comparison_text)
        if left is None or right is None:
            return False
        return left < right if comparator == "before" else left > right

    if comparator == "regexMatch":
        try:
            return re.search(comparison_text, user_text) is not None
        except re.error:
            return False
    if comparator == "regexNotMatch":
        try:
            return re.search(comparison_text, user_text) is None
        except re.error:
            return False

    if comparator == "arrayContains" and isinstance(user_value, list):
        comparison_values = [
            str(item) for item in _as_list(comparison_value, comparison_text)
        ]
        user_values = [str(item) for item in user_value]
        return all(item in user_values for item in comparison_values)
    if comparator == "arrayNotContains" and isinstance(user_value, list):
        comparison_values = [
            str(item) for item in _as_list(comparison_value, comparison_text)
        ]
        user_values = [str(item) for item in user_value]
        return not any(item in user_values for item in comparison_values)

    return False


def _as_list(value: Any, fallback: str) -> List[Any]:
    if isinstance(value, list):
        return value
    return [fallback]


def _parse_semver(value: str) -> Optional[Tuple[int, int, int]]:
    match = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", value.strip())
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2) or 0),
        int(match.group(3) or 0),
    )


def _compare_semver(left: Tuple[int, int, int], right: Tuple[int, int, int]) -> int:
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def _parse_datetime(value: str) -> Optional[datetime]:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None

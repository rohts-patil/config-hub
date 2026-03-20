from __future__ import annotations

"""Targeting engine — client-side flag evaluation logic.

This module evaluates feature flags against a user context using the config JSON
structure fetched from the SDK endpoint. It supports:
- All comparators (text, numeric, semver, datetime, regex, array, list)
- Rule evaluation: iterate top-down, AND within a rule, first match wins
- Percentage rollout: SHA256(settingKey + userId) → deterministic bucket (0–99)
"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def evaluate_flag(
    setting_key: str,
    setting_data: dict,
    user: Optional[Dict[str, Any]] = None,
    segments: Optional[List[dict]] = None,
) -> Any:
    """Evaluate a single flag for a given user context.

    Args:
        setting_key: The flag key (used for percentage hashing).
        setting_data: The setting object from config JSON.
        user: User attributes dict, e.g. {"identifier": "user123", "email": "a@b.com"}.
        segments: List of segment definitions from config JSON.

    Returns:
        The resolved flag value.
    """
    if user is None:
        user = {}
    if segments is None:
        segments = []

    # 1. Evaluate targeting rules (first match wins)
    for rule in setting_data.get("targetingRules", []):
        conditions = rule.get("conditions", [])
        if conditions and _all_conditions_match(conditions, user, segments):
            return rule.get("value")

    # 2. Evaluate percentage options
    percentage_options = setting_data.get("percentageOptions", [])
    if percentage_options:
        identifier = user.get("identifier", "")
        if identifier:
            bucket = _get_percentage_bucket(setting_key, identifier)
            cumulative = 0
            for option in percentage_options:
                cumulative += option.get("percentage", 0)
                if bucket < cumulative:
                    return option.get("value")

    # 3. Return default value
    return setting_data.get("value")


def evaluate_all_flags(
    config_json: dict,
    user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate all flags in a config JSON for a given user."""
    segments = config_json.get("segments", [])
    results = {}
    for key, setting_data in config_json.get("settings", {}).items():
        results[key] = evaluate_flag(key, setting_data, user, segments)
    return results


def _get_percentage_bucket(setting_key: str, user_id: str) -> int:
    """Deterministic percentage bucket (0–99) using SHA256."""
    hash_input = f"{setting_key}{user_id}"
    hash_hex = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return int(hash_hex[:8], 16) % 100


def _all_conditions_match(
    conditions: List[dict],
    user: Dict[str, Any],
    segments: List[dict],
) -> bool:
    """All conditions in a rule must match (AND logic)."""
    return all(_condition_matches(c, user, segments) for c in conditions)


def _condition_matches(
    condition: dict,
    user: Dict[str, Any],
    segments: List[dict],
) -> bool:
    """Evaluate a single condition."""
    cond_type = condition.get("type", "user")

    if cond_type == "segment":
        segment_id = condition.get("segmentId")
        comparator = condition.get("comparator", "isOneOf")
        for seg in segments:
            if seg.get("id") == segment_id:
                seg_matches = _all_conditions_match(
                    seg.get("conditions", []), user, segments
                )
                if comparator in ("isOneOf", "equals"):
                    return seg_matches
                elif comparator in ("isNotOneOf", "notEquals"):
                    return not seg_matches
        return False

    if cond_type == "flag":
        # Prerequisite flag — not evaluated here (would need full config context)
        return True

    # User condition
    attribute = condition.get("attribute", "")
    comparator = condition.get("comparator", "")
    comparison_value = condition.get("comparisonValue")
    user_value = user.get(attribute)

    if user_value is None:
        return False

    return _compare(comparator, user_value, comparison_value)



def _compare(comparator: str, user_value: Any, comparison_value: Any) -> bool:
    """Apply a comparator to user_value vs comparison_value."""
    uv = str(user_value)
    cv = str(comparison_value) if comparison_value is not None else ""

    # ── Text comparators ──
    if comparator == "equals":
        return uv == cv
    elif comparator == "notEquals":
        return uv != cv
    elif comparator == "contains":
        return cv in uv
    elif comparator == "notContains":
        return cv not in uv
    elif comparator == "startsWith":
        return uv.startswith(cv)
    elif comparator == "notStartsWith":
        return not uv.startswith(cv)
    elif comparator == "endsWith":
        return uv.endswith(cv)
    elif comparator == "notEndsWith":
        return not uv.endswith(cv)

    # ── List comparators ──
    elif comparator == "isOneOf":
        items = comparison_value if isinstance(comparison_value, list) else [cv]
        return uv in [str(i) for i in items]
    elif comparator == "isNotOneOf":
        items = comparison_value if isinstance(comparison_value, list) else [cv]
        return uv not in [str(i) for i in items]

    # ── Numeric comparators ──
    elif comparator in (
        "numberEquals", "numberNotEquals",
        "numberLess", "numberLessOrEquals",
        "numberGreater", "numberGreaterOrEquals",
    ):
        try:
            nv = float(user_value)
            nc = float(comparison_value)
        except (ValueError, TypeError):
            return False
        if comparator == "numberEquals":
            return nv == nc
        elif comparator == "numberNotEquals":
            return nv != nc
        elif comparator == "numberLess":
            return nv < nc
        elif comparator == "numberLessOrEquals":
            return nv <= nc
        elif comparator == "numberGreater":
            return nv > nc
        elif comparator == "numberGreaterOrEquals":
            return nv >= nc

    # ── Semver comparators ──
    elif comparator in (
        "semverLess", "semverLessOrEquals",
        "semverGreater", "semverGreaterOrEquals",
        "semverEquals", "semverNotEquals",
    ):
        uv_parts = _parse_semver(uv)
        cv_parts = _parse_semver(cv)
        if uv_parts is None or cv_parts is None:
            return False
        if comparator == "semverEquals":
            return uv_parts == cv_parts
        elif comparator == "semverNotEquals":
            return uv_parts != cv_parts
        elif comparator == "semverLess":
            return uv_parts < cv_parts
        elif comparator == "semverLessOrEquals":
            return uv_parts <= cv_parts
        elif comparator == "semverGreater":
            return uv_parts > cv_parts
        elif comparator == "semverGreaterOrEquals":
            return uv_parts >= cv_parts

    # ── Datetime comparators ──
    elif comparator in ("before", "after"):
        try:
            udt = datetime.fromisoformat(uv)
            cdt = datetime.fromisoformat(cv)
        except (ValueError, TypeError):
            return False
        if comparator == "before":
            return udt < cdt
        elif comparator == "after":
            return udt > cdt

    # ── Regex comparators ──
    elif comparator == "regexMatch":
        try:
            return bool(re.search(cv, uv))
        except re.error:
            return False
    elif comparator == "regexNotMatch":
        try:
            return not bool(re.search(cv, uv))
        except re.error:
            return False

    # ── Array comparators ──
    elif comparator == "arrayContains":
        if isinstance(user_value, list):
            items = comparison_value if isinstance(comparison_value, list) else [comparison_value]
            return all(str(i) in [str(v) for v in user_value] for i in items)
        return False
    elif comparator == "arrayNotContains":
        if isinstance(user_value, list):
            items = comparison_value if isinstance(comparison_value, list) else [comparison_value]
            return not any(str(i) in [str(v) for v in user_value] for i in items)
        return False

    return False


def _parse_semver(version: str) -> Optional[tuple]:
    """Parse a semver string into a comparable tuple."""
    version = version.strip().lstrip("v")
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2) or 0),
        int(match.group(3) or 0),
    )

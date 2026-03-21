from __future__ import annotations

from typing import Any, Dict, List, TypedDict


UserObject = Dict[str, Any]


class Condition(TypedDict, total=False):
    type: str
    attribute: str
    comparator: str
    comparisonValue: Any
    segmentId: str
    prerequisiteFlagKey: str


class TargetingRule(TypedDict):
    conditions: List[Condition]
    value: Any


class PercentageOption(TypedDict):
    percentage: int
    value: Any


class SettingData(TypedDict, total=False):
    type: str
    value: Any
    targetingRules: List[TargetingRule]
    percentageOptions: List[PercentageOption]


class SegmentDefinition(TypedDict):
    id: str
    name: str
    conditions: List[Condition]


class ConfigJson(TypedDict):
    settings: Dict[str, SettingData]
    segments: List[SegmentDefinition]

import {
  Condition,
  ConfigJson,
  PercentageOption,
  SegmentDefinition,
  SettingData,
  TargetingRule,
  UserObject,
} from "./types";

/**
 * Evaluate a single flag for a given user context.
 *
 * 1. Iterate targeting rules top-down — first rule where ALL conditions match wins.
 * 2. If no rule matches, try percentage rollout (deterministic via SHA-256).
 * 3. Fall back to default value.
 */
export function evaluateFlag(
  settingKey: string,
  setting: SettingData,
  user?: UserObject,
  segments: SegmentDefinition[] = []
): unknown {
  // 1. Targeting rules
  if (setting.targetingRules) {
    for (const rule of setting.targetingRules) {
      if (
        rule.conditions.length > 0 &&
        allConditionsMatch(rule.conditions, user, segments)
      ) {
        return rule.value;
      }
    }
  }

  // 2. Percentage rollout
  if (setting.percentageOptions && setting.percentageOptions.length > 0) {
    const identifier = user?.identifier ?? "";
    if (identifier) {
      const bucket = getPercentageBucket(settingKey, identifier);
      let cumulative = 0;
      for (const opt of setting.percentageOptions) {
        cumulative += opt.percentage;
        if (bucket < cumulative) {
          return opt.value;
        }
      }
    }
  }

  // 3. Default
  return setting.value;
}

/** Evaluate all flags in a config JSON for a given user. */
export function evaluateAllFlags(
  config: ConfigJson,
  user?: UserObject
): Record<string, unknown> {
  const results: Record<string, unknown> = {};
  for (const [key, setting] of Object.entries(config.settings)) {
    results[key] = evaluateFlag(key, setting, user, config.segments);
  }
  return results;
}

// ── Internals ──

/**
 * Synchronous percentage bucket using a simple string hash.
 * We use a fast FNV-1a-like hash so evaluation stays synchronous.
 */
function getPercentageBucket(settingKey: string, userId: string): number {
  const input = settingKey + userId;
  let hash = 2166136261;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = (hash * 16777619) >>> 0;
  }
  return hash % 100;
}

function allConditionsMatch(
  conditions: Condition[],
  user: UserObject | undefined,
  segments: SegmentDefinition[]
): boolean {
  return conditions.every((c) => conditionMatches(c, user, segments));
}

function conditionMatches(
  cond: Condition,
  user: UserObject | undefined,
  segments: SegmentDefinition[]
): boolean {
  const condType = cond.type ?? "user";

  if (condType === "segment") {
    const seg = segments.find((s) => s.id === cond.segmentId);
    if (!seg) return false;
    const segMatches = allConditionsMatch(seg.conditions, user, segments);
    const comp = cond.comparator ?? "isOneOf";
    if (comp === "isOneOf" || comp === "equals") return segMatches;
    if (comp === "isNotOneOf" || comp === "notEquals") return !segMatches;
    return false;
  }

  if (condType === "flag") {
    // Prerequisite flag — not supported in client-side eval without full context
    return true;
  }

  // User condition
  if (!user) return false;
  const attr = cond.attribute ?? "";
  const userValue = user[attr];
  if (userValue === undefined || userValue === null) return false;

  return compare(cond.comparator, userValue, cond.comparisonValue);
}

function compare(
  comparator: string,
  userValue: unknown,
  comparisonValue: unknown
): boolean {
  const uv = String(userValue);
  const cv = comparisonValue != null ? String(comparisonValue) : "";

  // ── Text ──
  if (comparator === "equals") return uv === cv;
  if (comparator === "notEquals") return uv !== cv;
  if (comparator === "contains") return uv.includes(cv);
  if (comparator === "notContains") return !uv.includes(cv);
  if (comparator === "startsWith") return uv.startsWith(cv);

  // ── List ──
  if (comparator === "isOneOf") {
    const items = Array.isArray(comparisonValue)
      ? comparisonValue.map(String)
      : [cv];
    return items.includes(uv);
  }
  if (comparator === "isNotOneOf") {
    const items = Array.isArray(comparisonValue)
      ? comparisonValue.map(String)
      : [cv];
    return !items.includes(uv);
  }

  // ── Numeric ──
  if (comparator.startsWith("number")) {
    const nv = parseFloat(String(userValue));
    const nc = parseFloat(String(comparisonValue));
    if (isNaN(nv) || isNaN(nc)) return false;
    if (comparator === "numberEquals") return nv === nc;
    if (comparator === "numberNotEquals") return nv !== nc;
    if (comparator === "numberLess") return nv < nc;
    if (comparator === "numberLessOrEquals") return nv <= nc;
    if (comparator === "numberGreater") return nv > nc;
    if (comparator === "numberGreaterOrEquals") return nv >= nc;
  }

  // ── Semver ──
  if (comparator.startsWith("semver")) {
    const uvp = parseSemver(uv);
    const cvp = parseSemver(cv);
    if (!uvp || !cvp) return false;
    const cmp = compareSemver(uvp, cvp);
    if (comparator === "semverEquals") return cmp === 0;
    if (comparator === "semverNotEquals") return cmp !== 0;
    if (comparator === "semverLess") return cmp < 0;
    if (comparator === "semverLessOrEquals") return cmp <= 0;
    if (comparator === "semverGreater") return cmp > 0;
    if (comparator === "semverGreaterOrEquals") return cmp >= 0;
  }

  // ── Datetime ──
  if (comparator === "before" || comparator === "after") {
    const ud = new Date(uv).getTime();
    const cd = new Date(cv).getTime();
    if (isNaN(ud) || isNaN(cd)) return false;
    return comparator === "before" ? ud < cd : ud > cd;
  }

  // ── Regex ──
  if (comparator === "regexMatch") {
    try {
      return new RegExp(cv).test(uv);
    } catch {
      return false;
    }
  }
  if (comparator === "regexNotMatch") {
    try {
      return !new RegExp(cv).test(uv);
    } catch {
      return false;
    }
  }

  // ── Array ──
  if (comparator === "arrayContains" && Array.isArray(userValue)) {
    const items = Array.isArray(comparisonValue)
      ? comparisonValue.map(String)
      : [String(comparisonValue)];
    const uvArr = (userValue as unknown[]).map(String);
    return items.every((i) => uvArr.includes(i));
  }
  if (comparator === "arrayNotContains" && Array.isArray(userValue)) {
    const items = Array.isArray(comparisonValue)
      ? comparisonValue.map(String)
      : [String(comparisonValue)];
    const uvArr = (userValue as unknown[]).map(String);
    return !items.some((i) => uvArr.includes(i));
  }

  return false;
}

type SemverTuple = [number, number, number];

function parseSemver(version: string): SemverTuple | null {
  const v = version.trim().replace(/^v/, "");
  const match = v.match(/^(\d+)(?:\.(\d+))?(?:\.(\d+))?/);
  if (!match) return null;
  return [
    parseInt(match[1], 10),
    parseInt(match[2] ?? "0", 10),
    parseInt(match[3] ?? "0", 10),
  ];
}

function compareSemver(a: SemverTuple, b: SemverTuple): number {
  for (let i = 0; i < 3; i++) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return 0;
}

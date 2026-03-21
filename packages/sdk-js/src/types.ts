/** User context passed to flag evaluation. */
export interface UserObject {
  identifier: string;
  [key: string]: string | number | boolean | string[];
}

/** Options for creating a ConfigHub client. */
export interface ConfigHubOptions {
  /** Base URL of the ConfigHub backend (e.g. "http://localhost:8000"). */
  baseUrl: string;
  /** Polling interval in seconds. Default: 60. Set to 0 to disable polling. */
  pollIntervalSeconds?: number;
  /** Called whenever the config JSON changes after a poll. */
  onConfigChanged?: (config: ConfigJson) => void;
  /** Called after every flag evaluation. */
  onFlagEvaluated?: (key: string, value: unknown, user?: UserObject) => void;
  /** Custom fetch implementation (for Node.js or testing). */
  fetchFn?: typeof fetch;
}

/** A single condition in a targeting rule. */
export interface Condition {
  type: string;
  attribute?: string;
  comparator: string;
  comparisonValue?: unknown;
  segmentId?: string;
  prerequisiteFlagKey?: string;
}

/** A targeting rule: all conditions must match (AND). */
export interface TargetingRule {
  conditions: Condition[];
  value: unknown;
}

/** A percentage rollout option. */
export interface PercentageOption {
  percentage: number;
  value: unknown;
}

/** A single setting (flag) in the config JSON. */
export interface SettingData {
  type: string;
  value: unknown;
  targetingRules?: TargetingRule[];
  percentageOptions?: PercentageOption[];
}

/** A segment definition. */
export interface SegmentDefinition {
  id: string;
  name: string;
  conditions: Condition[];
}

/** The full config JSON returned by the SDK endpoint. */
export interface ConfigJson {
  settings: Record<string, SettingData>;
  segments: SegmentDefinition[];
}


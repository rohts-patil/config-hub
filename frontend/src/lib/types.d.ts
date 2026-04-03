// ── Auth ──
interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

// ── Organization ──
interface Organization {
  id: string;
  name: string;
  created_at: string;
}

interface OrgMember {
  id: string;
  user_id: string;
  role: string;
  user?: User;
}

interface OrgInvite {
  id: string;
  email: string;
  role: string;
  created_at: string;
}

interface PermissionGroup {
  id: string;
  product_id: string;
  name: string;
  permissions: Record<string, boolean>;
}

// ── Product ──
interface Product {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  created_at: string;
}

// ── Config ──
interface Config {
  id: string;
  product_id: string;
  name: string;
  description?: string;
  order: number;
  created_at: string;
}

// ── Environment ──
interface Environment {
  id: string;
  product_id: string;
  name: string;
  color: string;
  order: number;
  created_at: string;
}

// ── Setting (Feature Flag) ──
interface Setting {
  id: string;
  config_id: string;
  key: string;
  name: string;
  setting_type: string;
  hint?: string;
  order: number;
  created_at: string;
}

// ── Setting Value + Targeting ──
interface Condition {
  id: string;
  condition_type: string;
  attribute?: string;
  comparator: string;
  comparison_value: Record<string, unknown>;
  segment_id?: string;
  prerequisite_setting_id?: string;
}

interface TargetingRule {
  id: string;
  served_value: Record<string, unknown>;
  order: number;
  conditions: Condition[];
}

interface PercentageOption {
  id: string;
  percentage: number;
  value: Record<string, unknown>;
  order: number;
}

interface SettingValue {
  id: string;
  setting_id: string;
  environment_id: string;
  default_value: Record<string, unknown>;
  targeting_rules: TargetingRule[];
  percentage_options: PercentageOption[];
}

interface ConditionIn {
  condition_type?: string;
  attribute?: string;
  comparator: string;
  comparison_value: Record<string, unknown>;
  segment_id?: string;
  prerequisite_setting_id?: string;
}

interface TargetingRuleIn {
  served_value: Record<string, unknown>;
  conditions: ConditionIn[];
  order?: number;
}

interface PercentageOptionIn {
  percentage: number;
  value: Record<string, unknown>;
  order?: number;
}

interface SettingValueUpdate {
  default_value: Record<string, unknown>;
  targeting_rules: TargetingRuleIn[];
  percentage_options: PercentageOptionIn[];
}

// ── Segment ──
interface SegmentCondition {
  attribute: string;
  comparator: string;
  comparison_value: Record<string, unknown>;
}

interface Segment {
  id: string;
  product_id: string;
  name: string;
  description?: string;
  conditions: SegmentCondition[];
}

interface SegmentCreate {
  name: string;
  description?: string;
  conditions: SegmentCondition[];
}

// ── Tag ──
interface Tag {
  id: string;
  product_id: string;
  name: string;
  color: string;
}

// ── SDK Key ──
interface SDKKeySummary {
  id: string;
  config_id: string;
  environment_id: string;
  masked_key: string;
  revoked: boolean;
  created_at: string;
}

interface SDKKeySecret extends SDKKeySummary {
  key: string;
}

// ── Audit Log ──
interface AuditLogEntry {
  id: string;
  organization_id: string;
  user_id?: string;
  user?: {
    id: string;
    email: string;
    name: string;
  };
  context?: {
    entity_label?: string;
    entity_name?: string;
    setting_key?: string;
    setting_name?: string;
    environment_name?: string;
    config_name?: string;
    product_name?: string;
  };
  action: string;
  entity_type: string;
  entity_id?: string;
  old_value?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  reason?: string;
  created_at: string;
}

// ── Webhook ──
interface Webhook {
  id: string;
  product_id: string;
  url: string;
  config_id?: string;
  environment_id?: string;
  enabled: boolean;
  created_at: string;
}

interface GoogleCredentialResponse {
  credential?: string;
  select_by?: string;
}

interface GoogleIdConfiguration {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void | Promise<void>;
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
  context?: "signin" | "signup" | "use";
  ux_mode?: "popup" | "redirect";
}

interface GoogleButtonConfiguration {
  type?: "standard" | "icon";
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape?: "rectangular" | "pill" | "circle" | "square";
  width?: number | string;
  logo_alignment?: "left" | "center";
}

interface GoogleAccountsIdApi {
  initialize: (config: GoogleIdConfiguration) => void;
  renderButton: (
    parent: HTMLElement,
    options: GoogleButtonConfiguration
  ) => void;
}

interface Window {
  google?: {
    accounts: {
      id: GoogleAccountsIdApi;
    };
  };
}

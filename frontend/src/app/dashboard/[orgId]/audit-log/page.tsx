"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { History, ChevronDown } from "lucide-react";

const ENTITY_TYPES = [
  "all",
  "organization",
  "product",
  "config",
  "environment",
  "setting",
  "setting_value",
  "segment",
  "tag",
  "webhook",
];

function humanizeLabel(value: string) {
  return value.replace(/_/g, " ");
}

function normalizeAuditValue(value: unknown): unknown {
  if (
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    "v" in (value as Record<string, unknown>) &&
    Object.keys(value as Record<string, unknown>).length === 1
  ) {
    return (value as Record<string, unknown>).v;
  }

  if (Array.isArray(value)) {
    return value.map(normalizeAuditValue);
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(
        ([key, innerValue]) => [key, normalizeAuditValue(innerValue)]
      )
    );
  }

  return value;
}

function formatAuditValue(value: unknown): string {
  const normalized = normalizeAuditValue(value);

  if (normalized === undefined) return "empty";
  if (normalized === null) return "empty";
  if (typeof normalized === "string") return normalized || "empty";
  if (typeof normalized === "number" || typeof normalized === "boolean") {
    return String(normalized);
  }

  if (Array.isArray(normalized)) {
    return normalized.map((item) => formatAuditValue(item)).join(", ");
  }

  return JSON.stringify(normalized);
}

function valuesAreEqual(left: unknown, right: unknown) {
  return (
    JSON.stringify(normalizeAuditValue(left)) ===
    JSON.stringify(normalizeAuditValue(right))
  );
}

function summarizeFields(values?: Record<string, unknown>) {
  if (!values) return [];

  return Object.entries(values)
    .slice(0, 4)
    .map(([key, value]) => `${humanizeLabel(key)}: ${formatAuditValue(value)}`);
}

function getEntityLabel(entry: AuditLogEntry) {
  return (
    entry.context?.entity_label ||
    entry.context?.entity_name ||
    (typeof entry.new_value?.setting_key === "string"
      ? `${entry.new_value.setting_key}${entry.new_value.environment_name ? ` in ${entry.new_value.environment_name}` : ""}`
      : undefined) ||
    (typeof entry.new_value?.name === "string"
      ? entry.new_value.name
      : undefined) ||
    (typeof entry.old_value?.name === "string"
      ? entry.old_value.name
      : undefined)
  );
}

function describeSettingValueEntry(entry: AuditLogEntry) {
  const label =
    getEntityLabel(entry) ||
    entry.context?.setting_key ||
    humanizeLabel(entry.entity_type);
  const oldValue = entry.old_value ?? {};
  const newValue = entry.new_value ?? {};
  const details: string[] = [];

  if (!valuesAreEqual(oldValue.default_value, newValue.default_value)) {
    details.push(
      `Default value changed from ${formatAuditValue(oldValue.default_value)} to ${formatAuditValue(newValue.default_value)}`
    );
  }

  if (!valuesAreEqual(oldValue.targeting_rules, newValue.targeting_rules)) {
    const nextRuleCount = Array.isArray(newValue.targeting_rules)
      ? newValue.targeting_rules.length
      : 0;
    details.push(
      nextRuleCount > 0
        ? `Targeting rules updated (${nextRuleCount} rule${nextRuleCount === 1 ? "" : "s"} now active)`
        : "Targeting rules cleared"
    );
  }

  if (
    !valuesAreEqual(oldValue.percentage_options, newValue.percentage_options)
  ) {
    const rollout = Array.isArray(newValue.percentage_options)
      ? newValue.percentage_options
          .map((option) => {
            if (!option || typeof option !== "object") return null;
            const typedOption = option as Record<string, unknown>;
            return `${typedOption.percentage}% => ${formatAuditValue(typedOption.value)}`;
          })
          .filter(Boolean)
          .join(", ")
      : "";

    details.push(
      rollout
        ? `Percentage rollout updated: ${rollout}`
        : "Percentage rollout cleared"
    );
  }

  return {
    title: `Updated ${label}`,
    details:
      details.length > 0
        ? details
        : ["Targeting rules, rollout, or default value were refreshed."],
  };
}

function describeAuditEntry(entry: AuditLogEntry) {
  const entity = humanizeLabel(entry.entity_type);
  const action = entry.action.toLowerCase();
  const oldValue = entry.old_value ?? {};
  const newValue = entry.new_value ?? {};
  const label = getEntityLabel(entry);

  if (entry.entity_type === "setting_value") {
    return describeSettingValueEntry(entry);
  }

  if (action.includes("create")) {
    const details = summarizeFields(entry.new_value);
    return {
      title: label ? `Created ${label}` : `Created ${entity}`,
      details: details.length > 0 ? details : ["New record added."],
    };
  }

  if (action.includes("delete")) {
    const details = summarizeFields(entry.old_value);
    return {
      title: label ? `Deleted ${label}` : `Deleted ${entity}`,
      details: details.length > 0 ? details : ["Record removed."],
    };
  }

  const changedKeys = Array.from(
    new Set([...Object.keys(oldValue), ...Object.keys(newValue)])
  ).filter(
    (key) =>
      JSON.stringify(normalizeAuditValue(oldValue[key])) !==
      JSON.stringify(normalizeAuditValue(newValue[key]))
  );

  const details = changedKeys.slice(0, 5).map((key) => {
    const before = formatAuditValue(oldValue[key]);
    const after = formatAuditValue(newValue[key]);
    return `${humanizeLabel(key)} changed from ${before} to ${after}`;
  });

  return {
    title: label ? `Updated ${label}` : `Updated ${entity}`,
    details: details.length > 0 ? details : ["Values were refreshed."],
  };
}

function getActorLabel(entry: AuditLogEntry) {
  const name = entry.user?.name?.trim();
  if (name) return name;

  const email = entry.user?.email?.trim();
  if (email) return email;

  return entry.user_id ? `User ${entry.user_id.slice(0, 8)}` : "Unknown user";
}

export default function AuditLogPage() {
  const { orgId } = useParams() as { orgId: string };
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const loadLogs = async () => {
      try {
        const data = await api.auditLog.list(orgId, {
          entity_type: filter === "all" ? undefined : filter,
          limit,
          offset: 0,
        });
        if (cancelled) return;
        setEntries(data);
        setOffset(limit);
      } catch (err: any) {
        if (!cancelled) toast.error(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadLogs();
    return () => {
      cancelled = true;
    };
  }, [orgId, filter]);

  const loadMore = async () => {
    try {
      const data = await api.auditLog.list(orgId, {
        entity_type: filter === "all" ? undefined : filter,
        limit,
        offset,
      });
      setEntries((prev) => [...prev, ...data]);
      setOffset((prev) => prev + limit);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const actionColor = (action: string) => {
    if (action.includes("create")) return "default";
    if (action.includes("update")) return "secondary";
    if (action.includes("delete")) return "destructive";
    return "outline";
  };

  if (loading)
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audit Log</h1>
          <p className="text-muted-foreground">
            Track changes across your organization
          </p>
        </div>
        <Select value={filter} onValueChange={(v) => v && setFilter(v)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ENTITY_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {t === "all" ? "All entities" : t.replace("_", " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {entries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <History className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">No audit log entries.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-1">
          {entries.map((entry) => {
            const description = describeAuditEntry(entry);

            return (
              <div
                key={entry.id}
                className="flex items-start gap-4 rounded-2xl border border-white/50 bg-card/80 px-4 py-4 shadow-sm transition-colors hover:bg-card"
              >
                <div className="mt-1 h-2.5 w-2.5 rounded-full bg-primary shrink-0" />
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant={actionColor(entry.action) as any}>
                      {entry.action}
                    </Badge>
                    <Badge variant="outline">
                      {humanizeLabel(entry.entity_type)}
                    </Badge>
                    {getEntityLabel(entry) ? (
                      <Badge variant="outline" className="max-w-full">
                        <span className="truncate">
                          {getEntityLabel(entry)}
                        </span>
                      </Badge>
                    ) : (
                      entry.entity_id && (
                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                          {entry.entity_id.slice(0, 8)}
                        </code>
                      )
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {description.title}
                    </p>
                    <p className="mt-1 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
                      By {getActorLabel(entry)}
                    </p>
                    <div className="mt-1 space-y-1">
                      {description.details.map((detail) => (
                        <p
                          key={detail}
                          className="text-sm leading-6 text-muted-foreground"
                        >
                          {detail}
                        </p>
                      ))}
                    </div>
                  </div>
                  {entry.reason && (
                    <p className="text-sm rounded-xl bg-muted/60 px-3 py-2 text-muted-foreground">
                      {entry.reason}
                    </p>
                  )}
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap pt-0.5">
                  {new Date(entry.created_at).toLocaleString()}
                </span>
              </div>
            );
          })}
          <div className="flex justify-center pt-4">
            <Button variant="outline" size="sm" onClick={loadMore}>
              <ChevronDown className="mr-1 h-3 w-3" />
              Load More
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

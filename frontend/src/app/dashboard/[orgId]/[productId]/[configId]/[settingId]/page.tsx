"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { ArrowLeft, Plus, Trash2, Save, GripVertical } from "lucide-react";

const COMPARATOR_OPTIONS = [
  { value: "equals", label: "equals" },
  { value: "notEquals", label: "not equals" },
  { value: "contains", label: "contains" },
  { value: "notContains", label: "not contains" },
  { value: "startsWith", label: "starts with" },
  { value: "endsWith", label: "ends with" },
  { value: "isOneOf", label: "is one of" },
  { value: "isNotOneOf", label: "is not one of" },
  { value: "numberEquals", label: "= (num)" },
  { value: "numberLess", label: "< (num)" },
  { value: "numberGreater", label: "> (num)" },
  { value: "numberLessOrEquals", label: "≤ (num)" },
  { value: "numberGreaterOrEquals", label: "≥ (num)" },
  { value: "semverLess", label: "< (semver)" },
  { value: "semverGreater", label: "> (semver)" },
  { value: "semverEquals", label: "= (semver)" },
  { value: "before", label: "before" },
  { value: "after", label: "after" },
  { value: "regexMatch", label: "regex match" },
  { value: "regexNotMatch", label: "regex not match" },
  { value: "arrayContains", label: "array contains" },
  { value: "arrayNotContains", label: "array not contains" },
];

interface EditCond {
  condition_type: string;
  attribute: string;
  comparator: string;
  comparison_value: string;
  segment_id: string;
}
interface EditRule {
  served_value: string;
  conditions: EditCond[];
}
interface EditPct {
  percentage: number;
  value: string;
}

export default function FlagEditorPage() {
  const { orgId, productId, configId, settingId } = useParams() as {
    orgId: string;
    productId: string;
    configId: string;
    settingId: string;
  };
  const router = useRouter();
  const [setting, setSetting] = useState<Setting | null>(null);
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [selectedEnv, setSelectedEnv] = useState("");
  const [defaultValue, setDefaultValue] = useState("");
  const [rules, setRules] = useState<EditRule[]>([]);
  const [percentages, setPercentages] = useState<EditPct[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [s, e, seg] = await Promise.all([
          api.settings.get(configId, settingId),
          api.environments.list(productId),
          api.segments.list(productId),
        ]);
        setSetting(s);
        setEnvs(e);
        setSegments(seg);
        if (e.length > 0) setSelectedEnv(e[0].id);
      } catch (err: any) {
        toast.error(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [configId, settingId, productId]);

  useEffect(() => {
    if (!selectedEnv || !setting) return;
    (async () => {
      try {
        const sv = await api.settings.getValue(
          configId,
          settingId,
          selectedEnv
        );
        setDefaultValue(
          sv.default_value?.v !== undefined ? String(sv.default_value.v) : ""
        );
        setRules(
          sv.targeting_rules.map((r) => ({
            served_value:
              r.served_value?.v !== undefined ? String(r.served_value.v) : "",
            conditions: r.conditions.map((c) => ({
              condition_type: c.condition_type || "user",
              attribute: c.attribute || "",
              comparator: c.comparator,
              comparison_value:
                c.comparison_value?.v !== undefined
                  ? String(c.comparison_value.v)
                  : "",
              segment_id: c.segment_id || "",
            })),
          }))
        );
        setPercentages(
          sv.percentage_options.map((p) => ({
            percentage: p.percentage,
            value: p.value?.v !== undefined ? String(p.value.v) : "",
          }))
        );
      } catch {
        setDefaultValue(setting.setting_type === "boolean" ? "false" : "");
        setRules([]);
        setPercentages([]);
      }
    })();
  }, [selectedEnv, setting, configId, settingId]);

  const pv = (val: string, type: string): unknown => {
    if (type === "boolean") return val === "true";
    if (type === "int") return parseInt(val, 10) || 0;
    if (type === "double") return parseFloat(val) || 0;
    return val;
  };

  const segmentName = (segmentId: string) =>
    segments.find((segment) => segment.id === segmentId)?.name ||
    "Select segment";

  const handleSave = async () => {
    if (!setting || !selectedEnv) return;
    setSaving(true);
    try {
      await api.settings.updateValue(configId, settingId, selectedEnv, {
        default_value: { v: pv(defaultValue, setting.setting_type) },
        targeting_rules: rules.map((r, i) => ({
          served_value: { v: pv(r.served_value, setting.setting_type) },
          order: i,
          conditions: r.conditions.map((c) => ({
            condition_type: c.condition_type,
            attribute: c.condition_type === "user" ? c.attribute : undefined,
            comparator: c.comparator,
            comparison_value: { v: c.comparison_value },
            segment_id:
              c.condition_type === "segment" ? c.segment_id : undefined,
          })),
        })),
        percentage_options: percentages.map((p, i) => ({
          percentage: p.percentage,
          value: { v: pv(p.value, setting.setting_type) },
          order: i,
        })),
      });
      toast.success("Saved successfully");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const addRule = () =>
    setRules([
      ...rules,
      {
        served_value: "",
        conditions: [
          {
            condition_type: "user",
            attribute: "",
            comparator: "equals",
            comparison_value: "",
            segment_id: "",
          },
        ],
      },
    ]);
  const removeRule = (i: number) =>
    setRules(rules.filter((_, idx) => idx !== i));
  const addCond = (ri: number) => {
    const u = [...rules];
    u[ri].conditions.push({
      condition_type: "user",
      attribute: "",
      comparator: "equals",
      comparison_value: "",
      segment_id: "",
    });
    setRules(u);
  };
  const removeCond = (ri: number, ci: number) => {
    const u = [...rules];
    u[ri].conditions = u[ri].conditions.filter((_, i) => i !== ci);
    setRules(u);
  };
  const setCond = (
    ri: number,
    ci: number,
    f: keyof EditCond,
    v: string | null
  ) => {
    if (v === null) return;
    const u = [...rules];
    (u[ri].conditions[ci] as any)[f] = v;
    setRules([...u]);
  };
  const setRuleVal = (ri: number, v: string | null) => {
    if (v === null) return;
    const u = [...rules];
    u[ri].served_value = v;
    setRules([...u]);
  };
  const addPct = () =>
    setPercentages([...percentages, { percentage: 0, value: "" }]);
  const removePct = (i: number) =>
    setPercentages(percentages.filter((_, idx) => idx !== i));
  const setPct = (i: number, f: "percentage" | "value", v: string | null) => {
    if (v === null) return;
    const u = [...percentages];
    if (f === "percentage") u[i].percentage = parseInt(v, 10) || 0;
    else u[i].value = v;
    setPercentages([...u]);
  };
  const totalPct = percentages.reduce((s, p) => s + p.percentage, 0);

  if (loading || !setting)
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );

  const currentEnv = envs.find((e) => e.id === selectedEnv);
  const activeRulesCount = rules.length;
  const hasPercentageRollout = percentages.length > 0;

  return (
    <div className="space-y-6 max-w-5xl pb-12">
      {/* Header */}
      <div className="flex items-center gap-4 pb-4 border-b">
        <Button
          variant="ghost"
          size="icon"
          onClick={() =>
            router.push(`/dashboard/${orgId}/${productId}/${configId}`)
          }
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{setting.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <code className="bg-muted px-2 py-1 rounded text-xs">
              {setting.key}
            </code>
            <Badge variant="secondary" className="text-xs">
              {setting.setting_type}
            </Badge>
          </div>
        </div>
        <Button onClick={handleSave} disabled={saving} size="lg">
          <Save className="mr-2 h-4 w-4" />
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      {/* Environment Selector - Sticky */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 pb-4 -mx-6 px-6 border-b">
        <Tabs
          value={selectedEnv}
          onValueChange={(v) => v && setSelectedEnv(String(v))}
          className="w-full"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                Environment
              </span>
              <TabsList className="h-12 p-1 bg-muted/50">
                {envs.map((env) => (
                  <TabsTrigger 
                    key={env.id} 
                    value={env.id} 
                    className="gap-2.5 px-6 h-10 data-[state=active]:shadow-md transition-all"
                    style={{
                      backgroundColor: selectedEnv === env.id ? env.color : undefined,
                      color: selectedEnv === env.id ? '#ffffff' : undefined,
                    }}
                  >
                    <span
                      className="h-3 w-3 rounded-full border-2"
                      style={{ 
                        backgroundColor: selectedEnv === env.id ? '#ffffff' : env.color,
                        borderColor: selectedEnv === env.id ? '#ffffff' : env.color,
                      }}
                    />
                    <span className="font-semibold text-base">{env.name}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            {currentEnv && (
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{activeRulesCount}</span>
                  <span>rule{activeRulesCount !== 1 ? 's' : ''}</span>
                </div>
                {hasPercentageRollout && (
                  <>
                    <span>•</span>
                    <span>Rollout active</span>
                  </>
                )}
              </div>
            )}
          </div>
        </Tabs>
      </div>

      <Tabs
        value={selectedEnv}
        onValueChange={(v) => v && setSelectedEnv(String(v))}
        className="w-full"
      >

        {envs.map((env) => (
          <TabsContent key={env.id} value={env.id} className="space-y-6 mt-6">
            {/* Default Value */}
            <Card className="border-2">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Default Value</CardTitle>
                <CardDescription className="text-sm">
                  Served when no targeting rule matches
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-3">
                {setting.setting_type === "boolean" ? (
                  <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                    <Switch
                      checked={defaultValue === "true"}
                      onCheckedChange={(v) => setDefaultValue(String(v))}
                      className="data-[state=checked]:bg-green-600"
                    />
                    <span className="text-base font-semibold">
                      {defaultValue === "true" ? "ON" : "OFF"}
                    </span>
                  </div>
                ) : (
                  <Input
                    value={defaultValue}
                    onChange={(e) => setDefaultValue(e.target.value)}
                    type={
                      setting.setting_type === "int" ||
                      setting.setting_type === "double"
                        ? "number"
                        : "text"
                    }
                    placeholder="Default value"
                    className="h-11"
                  />
                )}
              </CardContent>
            </Card>

            {/* Targeting Rules */}
            <Card className="border-2">
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
                <div className="space-y-1">
                  <CardTitle className="text-lg">Targeting Rules</CardTitle>
                  <CardDescription className="text-sm">
                    Rules evaluated top-down. First match wins.
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={addRule}>
                  <Plus className="mr-1.5 h-4 w-4" />
                  Add Rule
                </Button>
              </CardHeader>
              <CardContent className="space-y-4 pt-2">
                {rules.length === 0 && (
                  <div className="text-center py-8 bg-muted/30 rounded-lg border-2 border-dashed">
                    <p className="text-sm text-muted-foreground">
                      No targeting rules. Default value will always be served.
                    </p>
                  </div>
                )}
                {rules.map((rule, ri) => (
                  <div key={ri} className="rounded-lg border-2 bg-card p-4 space-y-4 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                        <span className="text-sm font-semibold">
                          Rule {ri + 1}
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => removeRule(ri)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>

                    {/* Conditions */}
                    <div className="space-y-3 pl-6 bg-muted/30 rounded-lg p-4">
                      <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        IF all conditions match:
                      </Label>
                      {rule.conditions.map((cond, ci) => (
                        <div key={ci} className="flex items-center gap-2 flex-wrap">
                          <Select
                            value={cond.condition_type}
                            onValueChange={(v) =>
                              setCond(ri, ci, "condition_type", v)
                            }
                          >
                            <SelectTrigger className="w-[130px] h-10">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="user">User</SelectItem>
                              <SelectItem value="segment">Segment</SelectItem>
                              <SelectItem value="prerequisite">
                                Prereq
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          {cond.condition_type === "user" && (
                            <Input
                              className="w-[150px] h-10"
                              placeholder="attribute"
                              value={cond.attribute}
                              onChange={(e) =>
                                setCond(ri, ci, "attribute", e.target.value)
                              }
                            />
                          )}
                          {cond.condition_type === "segment" && (
                            <Select
                              value={cond.segment_id}
                              onValueChange={(v) =>
                                setCond(ri, ci, "segment_id", v)
                              }
                            >
                              <SelectTrigger className="w-[170px] h-10">
                                <span className="truncate">
                                  {segmentName(cond.segment_id)}
                                </span>
                              </SelectTrigger>
                              <SelectContent>
                                {segments.map((seg) => (
                                  <SelectItem key={seg.id} value={seg.id}>
                                    {seg.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                          <Select
                            value={cond.comparator}
                            onValueChange={(v) =>
                              setCond(ri, ci, "comparator", v)
                            }
                          >
                            <SelectTrigger className="w-[170px] h-10">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {COMPARATOR_OPTIONS.map((c) => (
                                <SelectItem key={c.value} value={c.value}>
                                  {c.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input
                            className="flex-1 min-w-[150px] h-10"
                            placeholder="value"
                            value={cond.comparison_value}
                            onChange={(e) =>
                              setCond(
                                ri,
                                ci,
                                "comparison_value",
                                e.target.value
                              )
                            }
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 shrink-0 hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => removeCond(ri, ci)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      ))}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-8"
                        onClick={() => addCond(ri)}
                      >
                        <Plus className="mr-1.5 h-3.5 w-3.5" />
                        Add Condition
                      </Button>
                    </div>

                    <Separator className="my-3" />

                    {/* Served value */}
                    <div className="flex items-center gap-3 pl-6 bg-muted/30 rounded-lg p-4">
                      <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">
                        THEN serve:
                      </Label>
                      {setting.setting_type === "boolean" ? (
                        <Select
                          value={rule.served_value}
                          onValueChange={(v) => setRuleVal(ri, v)}
                        >
                          <SelectTrigger className="w-[120px] h-10">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="true">ON</SelectItem>
                            <SelectItem value="false">OFF</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input
                          className="w-[220px] h-10"
                          value={rule.served_value}
                          onChange={(e) => setRuleVal(ri, e.target.value)}
                          type={
                            setting.setting_type === "int" ||
                            setting.setting_type === "double"
                              ? "number"
                              : "text"
                          }
                        />
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Percentage Rollout */}
            <Card className="border-2">
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
                <div className="space-y-1">
                  <CardTitle className="text-lg">
                    Percentage Rollout
                  </CardTitle>
                  <CardDescription className="text-sm">
                    Split traffic by percentage when no rule matches
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={addPct}>
                  <Plus className="mr-1.5 h-4 w-4" />
                  Add Option
                </Button>
              </CardHeader>
              <CardContent className="space-y-3 pt-2">
                {percentages.length === 0 && (
                  <div className="text-center py-8 bg-muted/30 rounded-lg border-2 border-dashed">
                    <p className="text-sm text-muted-foreground">
                      No percentage rollout configured.
                    </p>
                  </div>
                )}
                {percentages.map((p, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                    <Input
                      className="w-[90px]"
                      type="number"
                      min={0}
                      max={100}
                      value={p.percentage}
                      onChange={(e) => setPct(i, "percentage", e.target.value)}
                    />
                    <span className="text-sm font-medium text-muted-foreground">%</span>
                    {setting.setting_type === "boolean" ? (
                      <Select
                        value={p.value}
                        onValueChange={(v) => setPct(i, "value", v)}
                      >
                        <SelectTrigger className="w-[100px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="true">ON</SelectItem>
                          <SelectItem value="false">OFF</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        className="flex-1"
                        value={p.value}
                        onChange={(e) => setPct(i, "value", e.target.value)}
                        type={
                          setting.setting_type === "int" ||
                          setting.setting_type === "double"
                            ? "number"
                            : "text"
                        }
                        placeholder="Value"
                      />
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive"
                      onClick={() => removePct(i)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
                {percentages.length > 0 && (
                  <div className="flex items-center gap-2 pt-2 border-t">
                    <span className="text-sm font-medium">Total:</span>
                    <span
                      className={`text-sm font-bold ${totalPct === 100 ? "text-green-600" : "text-destructive"}`}
                    >
                      {totalPct}%
                    </span>
                    {totalPct !== 100 && (
                      <span className="text-xs text-destructive">
                        (must equal 100%)
                      </span>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

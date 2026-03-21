"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Flag, Plus, Trash2, Pencil, Search } from "lucide-react";

export default function FlagListPage() {
  const { orgId, productId, configId } = useParams() as {
    orgId: string;
    productId: string;
    configId: string;
  };
  const [settings, setSettings] = useState<Setting[]>([]);
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [selectedEnv, setSelectedEnv] = useState<string>("");
  const [envValues, setEnvValues] = useState<Record<string, SettingValue>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKey, setNewKey] = useState("");
  const [newType, setNewType] = useState("boolean");
  const [newHint, setNewHint] = useState("");
  const router = useRouter();
  const selectedEnvMeta = envs.find((env) => env.id === selectedEnv);

  useEffect(() => {
    let cancelled = false;
    const loadData = async () => {
      try {
        const [s, e] = await Promise.all([
          api.settings.list(configId),
          api.environments.list(productId),
        ]);
        if (cancelled) return;
        setSettings(s);
        setEnvs(e);
        setSelectedEnv((current) => current || e[0]?.id || "");
      } catch (err: any) {
        if (!cancelled) toast.error(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadData();
    return () => {
      cancelled = true;
    };
  }, [configId, productId]);

  // Fetch values for selected environment
  useEffect(() => {
    if (!selectedEnv || settings.length === 0) return;
    const fetchValues = async () => {
      const vals: Record<string, SettingValue> = {};
      await Promise.all(
        settings.map(async (s) => {
          try {
            vals[s.id] = await api.settings.getValue(
              configId,
              s.id,
              selectedEnv
            );
          } catch {
            /* ignore missing values */
          }
        })
      );
      setEnvValues(vals);
    };
    fetchValues();
  }, [selectedEnv, settings, configId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.settings.create(configId, {
        name: newName,
        key: newKey,
        setting_type: newType,
        hint: newHint || undefined,
      });
      const refreshed = await api.settings.list(configId);
      setNewName("");
      setNewKey("");
      setNewType("boolean");
      setNewHint("");
      setDialogOpen(false);
      setSettings(refreshed);
      toast.success("Feature flag created");
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete flag "${name}"?`)) return;
    try {
      await api.settings.delete(configId, id);
      const refreshed = await api.settings.list(configId);
      setSettings(refreshed);
      setEnvValues((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      toast.success("Flag deleted");
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleToggle = async (setting: Setting) => {
    if (!selectedEnv) return;
    const sv = envValues[setting.id];
    if (!sv) return;
    const currentVal = sv.default_value?.v;
    if (typeof currentVal !== "boolean") return;
    try {
      await api.settings.updateValue(configId, setting.id, selectedEnv, {
        default_value: { v: !currentVal },
        targeting_rules:
          sv.targeting_rules?.map((r) => ({
            served_value: r.served_value,
            order: r.order,
            conditions: r.conditions.map((c) => ({
              condition_type: c.condition_type,
              attribute: c.attribute,
              comparator: c.comparator,
              comparison_value: c.comparison_value,
              segment_id: c.segment_id,
              prerequisite_setting_id: c.prerequisite_setting_id,
            })),
          })) || [],
        percentage_options:
          sv.percentage_options?.map((p) => ({
            percentage: p.percentage,
            value: p.value,
            order: p.order,
          })) || [],
      });
      setEnvValues((prev) => ({
        ...prev,
        [setting.id]: { ...sv, default_value: { v: !currentVal } },
      }));
      toast.success(`Flag ${!currentVal ? "enabled" : "disabled"}`);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const filtered = settings.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.key.toLowerCase().includes(search.toLowerCase())
  );

  const typeColors: Record<string, string> = {
    boolean: "bg-green-500/10 text-green-700",
    string: "bg-blue-500/10 text-blue-700",
    int: "bg-purple-500/10 text-purple-700",
    double: "bg-orange-500/10 text-orange-700",
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
          <h1 className="text-2xl font-bold">Feature Flags</h1>
          <p className="text-muted-foreground">
            Manage feature flags for this config
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Flag
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Feature Flag</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="My Feature"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Key</Label>
                <Input
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="my_feature"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={newType}
                  onValueChange={(v) => v && setNewType(v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="boolean">Boolean</SelectItem>
                    <SelectItem value="string">String</SelectItem>
                    <SelectItem value="int">Integer</SelectItem>
                    <SelectItem value="double">Double</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Hint</Label>
                <Input
                  value={newHint}
                  onChange={(e) => setNewHint(e.target.value)}
                  placeholder="Optional hint"
                />
              </div>
              <Button type="submit" className="w-full">
                Create
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search flags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        {envs.length > 0 && (
          <Select
            value={selectedEnv}
            onValueChange={(v) => v && setSelectedEnv(v)}
          >
            <SelectTrigger className="w-48">
              <span className="flex items-center gap-2 truncate">
                {selectedEnvMeta && (
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: selectedEnvMeta.color }}
                  />
                )}
                {selectedEnvMeta?.name || "Select environment"}
              </span>
            </SelectTrigger>
            <SelectContent>
              {envs.map((env) => (
                <SelectItem key={env.id} value={env.id}>
                  <span className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: env.color }}
                    />
                    {env.name}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Flag className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              {settings.length === 0
                ? "No feature flags yet."
                : "No flags match your search."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Value</TableHead>
                {selectedEnv && <TableHead>Enabled</TableHead>}
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((s) => {
                const sv = envValues[s.id];
                const val = sv?.default_value?.v;
                const isBool = s.setting_type === "boolean";
                return (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                        {s.key}
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={typeColors[s.setting_type] || ""}
                      >
                        {s.setting_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {val !== undefined ? String(val) : "—"}
                    </TableCell>
                    {selectedEnv && (
                      <TableCell>
                        {isBool && sv ? (
                          <Switch
                            checked={!!val}
                            onCheckedChange={() => handleToggle(s)}
                          />
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    )}
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() =>
                            router.push(
                              `/dashboard/${orgId}/${productId}/${configId}/${s.id}`
                            )
                          }
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          onClick={() => handleDelete(s.id, s.name)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

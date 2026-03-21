"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  Key,
  Copy,
  Check,
  Plus,
  Eye,
  EyeOff,
  Trash2,
  ShieldBan,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function SDKKeysPage() {
  const { productId } = useParams() as { productId: string };
  const [configs, setConfigs] = useState<Config[]>([]);
  const [selectedConfig, setSelectedConfig] = useState("");
  const [keys, setKeys] = useState<SDKKeySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState("");
  const [creating, setCreating] = useState(false);
  const [generatedKey, setGeneratedKey] = useState<SDKKeySecret | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [actingKeyId, setActingKeyId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [c, e] = await Promise.all([
          api.configs.list(productId),
          api.environments.list(productId),
        ]);
        setConfigs(c);
        setEnvs(e);
        if (c.length > 0) setSelectedConfig(c[0].id);
      } catch (err: any) {
        toast.error(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [productId]);

  useEffect(() => {
    if (!selectedConfig) return;
    (async () => {
      try {
        setKeys(await api.sdkKeys.list(productId, selectedConfig));
      } catch {
        setKeys([]);
      }
    })();
  }, [selectedConfig, productId]);

  useEffect(() => {
    if (!generateOpen) return;
    setSelectedEnv((current) => current || envs[0]?.id || "");
  }, [generateOpen, envs]);

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const openGenerateDialog = () => {
    if (configs.length === 0) {
      toast.error("Create a config before generating an SDK key");
      return;
    }

    setGenerateOpen(true);
  };

  const handleGenerateKey = async () => {
    if (!selectedConfig || !selectedEnv) {
      toast.error("Choose a config and environment first");
      return;
    }

    try {
      setCreating(true);
      const key = await api.sdkKeys.create(productId, {
        config_id: selectedConfig,
        environment_id: selectedEnv,
      });
      setGeneratedKey(key);
      setKeys(await api.sdkKeys.list(productId, selectedConfig));
      toast.success("SDK key generated");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const closeGenerateDialog = (open: boolean) => {
    setGenerateOpen(open);
    if (!open) {
      setGeneratedKey(null);
      setSelectedEnv("");
      setCreating(false);
    }
  };

  const resetGeneratedKeyState = () => {
    if (generatedKey) {
      setVisibleKeys((current) => {
        const next = { ...current };
        delete next[generatedKey.id];
        return next;
      });
    }
    setGeneratedKey(null);
    setCopied(null);
  };

  const envName = (id: string) => envs.find((e) => e.id === id)?.name || id;
  const selectedConfigName =
    configs.find((config) => config.id === selectedConfig)?.name ||
    "Selected config";
  const selectedConfigLabel =
    configs.find((config) => config.id === selectedConfig)?.name ||
    "Select config";
  const selectedEnvLabel =
    envs.find((env) => env.id === selectedEnv)?.name || "Select environment";

  const isKeyVisible = (keyId: string) => Boolean(visibleKeys[keyId]);

  const toggleKeyVisibility = (keyId: string) => {
    setVisibleKeys((current) => ({
      ...current,
      [keyId]: !current[keyId],
    }));
  };

  const formatKey = (key: string, visible: boolean) => {
    if (visible) return key;
    return "********************";
  };

  const handleRevokeKey = async (sdkKeyId: string) => {
    if (
      !confirm("Revoke this SDK key? Existing SDKs using it will stop working.")
    ) {
      return;
    }

    try {
      setActingKeyId(sdkKeyId);
      await api.sdkKeys.revoke(productId, sdkKeyId);
      setKeys(await api.sdkKeys.list(productId, selectedConfig));
      toast.success("SDK key revoked");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setActingKeyId(null);
    }
  };

  const handleDeleteKey = async (sdkKeyId: string) => {
    if (!confirm("Delete this SDK key permanently?")) return;

    try {
      setActingKeyId(sdkKeyId);
      await api.sdkKeys.delete(productId, sdkKeyId);
      setKeys(await api.sdkKeys.list(productId, selectedConfig));
      toast.success("SDK key deleted");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setActingKeyId(null);
    }
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
          <h1 className="text-2xl font-bold">SDK Keys</h1>
          <p className="text-muted-foreground">
            Keys for connecting SDKs to your configs
          </p>
        </div>
        <div className="flex items-center gap-3">
          {configs.length > 0 && (
            <Select
              value={selectedConfig}
              onValueChange={(v) => v && setSelectedConfig(v)}
            >
              <SelectTrigger className="w-[200px]">
                <span className="truncate">{selectedConfigLabel}</span>
              </SelectTrigger>
              <SelectContent>
                {configs.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button
            onClick={openGenerateDialog}
            disabled={loading}
            className="relative z-10 shrink-0"
          >
            <Plus className="mr-2 h-4 w-4" />
            Generate Key
          </Button>
        </div>
      </div>

      {keys.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Key className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              No SDK keys found for this config.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Environment</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-[148px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((k) => (
                <TableRow key={k.id}>
                  <TableCell className="max-w-[320px] font-mono text-sm">
                    <div className="space-y-1">
                      <span className="block truncate">{k.masked_key}</span>
                      <p className="text-xs font-normal text-muted-foreground">
                        Full value is only shown once when the key is generated.
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>{envName(k.environment_id)}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={
                        k.revoked
                          ? "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"
                          : "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300"
                      }
                    >
                      <span
                        className={
                          k.revoked
                            ? "size-1.5 rounded-full bg-rose-500"
                            : "size-1.5 rounded-full bg-emerald-500"
                        }
                      />
                      {k.revoked ? "Revoked" : "Active"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(k.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {!k.revoked && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-amber-600 hover:text-amber-700"
                          onClick={() => handleRevokeKey(k.id)}
                          disabled={actingKeyId === k.id}
                          aria-label="Revoke SDK key"
                        >
                          <ShieldBan className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => handleDeleteKey(k.id)}
                        disabled={actingKeyId === k.id}
                        aria-label="Delete SDK key"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      <Dialog open={generateOpen} onOpenChange={closeGenerateDialog}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Generate SDK Key</DialogTitle>
            <DialogDescription>
              Create a new SDK key for {selectedConfigName}. Pick the
              environment this key should target.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Environment</p>
              {envs.length === 0 ? (
                <div className="rounded-xl border border-border/70 bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
                  Create an environment for this product before generating an
                  SDK key.
                </div>
              ) : (
                <Select
                  value={selectedEnv}
                  onValueChange={(value) => value && setSelectedEnv(value)}
                  disabled={creating || Boolean(generatedKey)}
                >
                  <SelectTrigger>
                    <span className="truncate">{selectedEnvLabel}</span>
                  </SelectTrigger>
                  <SelectContent>
                    {envs.map((env) => (
                      <SelectItem key={env.id} value={env.id}>
                        {env.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {generatedKey && (
              <div className="space-y-2 rounded-2xl border border-border/70 bg-muted/50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">New key created</p>
                    <p className="text-xs text-muted-foreground">
                      Copy it now. You can only see the full value in this
                      screen and your browser session.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => toggleKeyVisibility(generatedKey.id)}
                      aria-label={
                        isKeyVisible(generatedKey.id)
                          ? "Mask generated SDK key"
                          : "Show generated SDK key"
                      }
                    >
                      {isKeyVisible(generatedKey.id) ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyKey(generatedKey.key)}
                    >
                      {copied === generatedKey.key ? (
                        <Check className="mr-2 h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="mr-2 h-4 w-4" />
                      )}
                      {copied === generatedKey.key ? "Copied" : "Copy"}
                    </Button>
                  </div>
                </div>
                <pre className="overflow-x-auto rounded-xl bg-background/80 p-3 text-xs text-foreground">
                  <code>
                    {formatKey(generatedKey.key, isKeyVisible(generatedKey.id))}
                  </code>
                </pre>
              </div>
            )}

            <div className="flex justify-end gap-2">
              {generatedKey ? (
                <>
                  <Button
                    variant="outline"
                    onClick={resetGeneratedKeyState}
                    disabled={creating}
                  >
                    Generate another key
                  </Button>
                  <Button onClick={() => closeGenerateDialog(false)}>
                    Done
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    onClick={() => closeGenerateDialog(false)}
                    disabled={creating}
                  >
                    Close
                  </Button>
                  <Button
                    onClick={handleGenerateKey}
                    disabled={
                      !selectedConfig ||
                      !selectedEnv ||
                      creating ||
                      envs.length === 0
                    }
                  >
                    {creating ? "Generating..." : "Generate key"}
                  </Button>
                </>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

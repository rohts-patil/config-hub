"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
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
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { Key, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function SDKKeysPage() {
  const { productId } = useParams() as { productId: string };
  const [configs, setConfigs] = useState<Config[]>([]);
  const [selectedConfig, setSelectedConfig] = useState("");
  const [keys, setKeys] = useState<SDKKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const [envs, setEnvs] = useState<Environment[]>([]);

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

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const envName = (id: string) => envs.find((e) => e.id === id)?.name || id;

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
        {configs.length > 0 && (
          <Select
            value={selectedConfig}
            onValueChange={(v) => v && setSelectedConfig(v)}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select config" />
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
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((k) => (
                <TableRow key={k.id}>
                  <TableCell className="font-mono text-sm">
                    {k.key.slice(0, 12)}...{k.key.slice(-4)}
                  </TableCell>
                  <TableCell>{envName(k.environment_id)}</TableCell>
                  <TableCell>
                    <Badge variant={k.revoked ? "destructive" : "default"}>
                      {k.revoked ? "Revoked" : "Active"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(k.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => copyKey(k.key)}
                    >
                      {copied === k.key ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

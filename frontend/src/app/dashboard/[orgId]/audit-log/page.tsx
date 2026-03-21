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
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="flex items-start gap-4 rounded-lg border px-4 py-3 hover:bg-muted/50 transition-colors"
            >
              <div className="mt-0.5 h-2 w-2 rounded-full bg-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant={actionColor(entry.action) as any}>
                    {entry.action}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {entry.entity_type}
                  </span>
                  {entry.entity_id && (
                    <code className="text-xs bg-muted px-1 rounded">
                      {entry.entity_id.slice(0, 8)}
                    </code>
                  )}
                </div>
                {entry.reason && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {entry.reason}
                  </p>
                )}
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {new Date(entry.created_at).toLocaleString()}
              </span>
            </div>
          ))}
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

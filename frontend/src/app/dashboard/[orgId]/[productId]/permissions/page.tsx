"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ShieldCheck, Plus, Trash2, PencilLine } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PERMISSION_OPTIONS = [
  {
    key: "canManageFlags",
    label: "Manage Flags",
    description: "Create, update, and remove configs and feature flag values.",
  },
  {
    key: "canManageEnvironments",
    label: "Manage Environments",
    description: "Create, edit, and delete product environments.",
  },
  {
    key: "canManageSegments",
    label: "Manage Segments",
    description: "Create and maintain rollout targeting segments.",
  },
  {
    key: "canManageTags",
    label: "Manage Tags",
    description: "Create and organize tag metadata for configs.",
  },
  {
    key: "canManageSdkKeys",
    label: "Manage SDK Keys",
    description: "Generate, revoke, and delete SDK keys.",
  },
  {
    key: "canManageWebhooks",
    label: "Manage Webhooks",
    description: "Configure outbound webhook integrations for this product.",
  },
  {
    key: "canViewAuditLog",
    label: "View Audit Log",
    description: "Access organization-level audit history for product changes.",
  },
] as const;

type PermissionKey = (typeof PERMISSION_OPTIONS)[number]["key"];
type PermissionValues = Record<PermissionKey, boolean>;

const DEFAULT_PERMISSIONS: PermissionValues = {
  canManageFlags: false,
  canManageEnvironments: false,
  canManageSegments: false,
  canManageTags: false,
  canManageSdkKeys: false,
  canManageWebhooks: false,
  canViewAuditLog: false,
};

function normalizePermissions(
  permissions?: Record<string, boolean>
): PermissionValues {
  const normalized = { ...DEFAULT_PERMISSIONS };
  for (const key of Object.keys(DEFAULT_PERMISSIONS) as PermissionKey[]) {
    normalized[key] = Boolean(permissions?.[key]);
  }
  return normalized;
}

export default function PermissionsPage() {
  const { productId } = useParams() as { productId: string };
  const [groups, setGroups] = useState<PermissionGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<PermissionGroup | null>(
    null
  );
  const [name, setName] = useState("");
  const [permissions, setPermissions] =
    useState<PermissionValues>(DEFAULT_PERMISSIONS);
  const [submitting, setSubmitting] = useState(false);
  const [actingGroupId, setActingGroupId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadGroups = async () => {
      try {
        const data = await api.permissions.list(productId);
        if (!cancelled) {
          setGroups(data);
        }
      } catch (err: any) {
        if (!cancelled) {
          toast.error(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadGroups();

    return () => {
      cancelled = true;
    };
  }, [productId]);

  const refreshGroups = async () => {
    const data = await api.permissions.list(productId);
    setGroups(data);
  };

  const resetForm = () => {
    setEditingGroup(null);
    setName("");
    setPermissions(DEFAULT_PERMISSIONS);
    setSubmitting(false);
  };

  const openCreateDialog = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEditDialog = (group: PermissionGroup) => {
    setEditingGroup(group);
    setName(group.name);
    setPermissions(normalizePermissions(group.permissions));
    setDialogOpen(true);
  };

  const handlePermissionToggle = (key: PermissionKey, checked: boolean) => {
    setPermissions((current) => ({
      ...current,
      [key]: checked,
    }));
  };

  const enabledCount = Object.values(permissions).filter(Boolean).length;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingGroup) {
        await api.permissions.update(productId, editingGroup.id, {
          name,
          permissions,
        });
        toast.success("Permission group updated");
      } else {
        await api.permissions.create(productId, {
          name,
          permissions,
        });
        toast.success("Permission group created");
      }

      await refreshGroups();
      setDialogOpen(false);
      resetForm();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (group: PermissionGroup) => {
    if (!confirm(`Delete permission group "${group.name}"?`)) {
      return;
    }

    setActingGroupId(group.id);
    try {
      await api.permissions.delete(productId, group.id);
      await refreshGroups();
      toast.success("Permission group deleted");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setActingGroupId(null);
    }
  };

  const closeDialog = (open: boolean) => {
    setDialogOpen(open);
    if (!open) {
      resetForm();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Permissions</h1>
          <p className="text-muted-foreground">
            Define reusable permission groups for this product.
          </p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="mr-2 h-4 w-4" />
          New Group
        </Button>
      </div>

      {groups.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <ShieldCheck className="mb-4 h-12 w-12 text-muted-foreground/50" />
            <p className="text-muted-foreground">
              No permission groups yet. Create your first one!
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Enabled Permissions</TableHead>
                <TableHead>Summary</TableHead>
                <TableHead className="w-[148px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map((group) => {
                const groupPermissions = normalizePermissions(
                  group.permissions
                );
                const activeKeys = PERMISSION_OPTIONS.filter(
                  ({ key }) => groupPermissions[key]
                );
                return (
                  <TableRow key={group.id}>
                    <TableCell className="font-medium">{group.name}</TableCell>
                    <TableCell>{activeKeys.length}</TableCell>
                    <TableCell className="max-w-[420px]">
                      <p className="line-clamp-2 text-sm text-muted-foreground">
                        {activeKeys.length > 0
                          ? activeKeys.map(({ label }) => label).join(", ")
                          : "No permissions enabled yet"}
                      </p>
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditDialog(group)}
                          disabled={actingGroupId === group.id}
                        >
                          <PencilLine className="h-4 w-4" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDelete(group)}
                          disabled={actingGroupId === group.id}
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

      <Dialog open={dialogOpen} onOpenChange={closeDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingGroup
                ? "Edit Permission Group"
                : "Create Permission Group"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="permission-group-name">Name</Label>
              <Input
                id="permission-group-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Release Managers"
                required
                disabled={submitting}
              />
            </div>

            <div className="rounded-2xl border border-border/70">
              <div className="border-b border-border/70 px-4 py-3">
                <p className="font-medium">Permission Matrix</p>
                <p className="text-sm text-muted-foreground">
                  {enabledCount} of {PERMISSION_OPTIONS.length} permissions
                  enabled
                </p>
              </div>
              <div className="divide-y divide-border/70">
                {PERMISSION_OPTIONS.map((option) => (
                  <div
                    key={option.key}
                    className="flex items-start justify-between gap-4 px-4 py-3"
                  >
                    <div>
                      <p className="font-medium">{option.label}</p>
                      <p className="text-sm text-muted-foreground">
                        {option.description}
                      </p>
                    </div>
                    <Switch
                      checked={permissions[option.key]}
                      onCheckedChange={(checked) =>
                        handlePermissionToggle(option.key, checked)
                      }
                      disabled={submitting}
                    />
                  </div>
                ))}
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting
                ? editingGroup
                  ? "Saving..."
                  : "Creating..."
                : editingGroup
                  ? "Save Changes"
                  : "Create Group"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

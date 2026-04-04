"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { Package, Plus, Trash2, Users } from "lucide-react";

export default function ProductsPage() {
  const { orgId } = useParams() as { orgId: string };
  const { user } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [invites, setInvites] = useState<OrgInvite[]>([]);
  const [inviteEmailsEnabled, setInviteEmailsEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(true);
  const [invitesLoading, setInvitesLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState("member");
  const [memberSubmitting, setMemberSubmitting] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteSubmitting, setInviteSubmitting] = useState(false);
  const [inviteActionId, setInviteActionId] = useState<string | null>(null);
  const [memberActionId, setMemberActionId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const router = useRouter();
  const currentMembership = members.find(
    (member) => member.user_id === user?.id
  );
  const isOrgAdmin = currentMembership?.role === "admin";
  const adminCount = members.filter((member) => member.role === "admin").length;

  useEffect(() => {
    let cancelled = false;
    const loadPage = async () => {
      try {
        const invitePromise = api.organizations
          .invites(orgId)
          .catch(() => [] as OrgInvite[]);
        const inviteSettingsPromise = api.organizations
          .inviteSettings(orgId)
          .catch(() => ({ invite_emails_enabled: false }));
        const [productData, memberData, inviteData, inviteSettings] =
          await Promise.all([
            api.products.list(orgId),
            api.organizations.members(orgId),
            invitePromise,
            inviteSettingsPromise,
          ]);
        if (!cancelled) {
          setProducts(productData);
          setMembers(memberData);
          setInvites(inviteData);
          setInviteEmailsEnabled(inviteSettings.invite_emails_enabled);
        }
      } catch (err: any) {
        if (!cancelled) toast.error(err.message);
      } finally {
        if (!cancelled) {
          setLoading(false);
          setMembersLoading(false);
          setInvitesLoading(false);
        }
      }
    };
    loadPage();
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  const refreshMembers = async () => {
    const data = await api.organizations.members(orgId);
    setMembers(data);
  };

  const refreshInvites = async () => {
    if (!isOrgAdmin) {
      setInvites([]);
      return;
    }
    const data = await api.organizations.invites(orgId);
    setInvites(data);
  };

  const refreshProducts = async () => {
    const data = await api.products.list(orgId);
    setProducts(data);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.products.create(orgId, {
        name: newName,
        description: newDesc || undefined,
      });
      const data = await api.products.list(orgId);
      setNewName("");
      setNewDesc("");
      setDialogOpen(false);
      setProducts(data);
      toast.success("Product created");
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete product "${name}"?`)) return;
    try {
      await api.products.delete(orgId, id);
      await refreshProducts();
      toast.success("Product deleted");
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setMemberSubmitting(true);
    try {
      await api.organizations.addMember(orgId, {
        email: memberEmail,
        role: memberRole,
      });
      await refreshMembers();
      setMemberEmail("");
      setMemberRole("member");
      toast.success("Member added");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setMemberSubmitting(false);
    }
  };

  const formatRole = (role: string) =>
    role
      .split("_")
      .map((segment) => segment[0].toUpperCase() + segment.slice(1))
      .join(" ");

  const handleRoleChange = (nextRole: string | null) => {
    if (nextRole) {
      setMemberRole(nextRole);
    }
  };

  const handleInviteRoleChange = (nextRole: string | null) => {
    if (nextRole) {
      setInviteRole(nextRole);
    }
  };

  const handleMemberRoleUpdate = async (
    memberId: string,
    nextRole: string | null,
    currentRole: string
  ) => {
    if (!nextRole || nextRole === currentRole) {
      return;
    }

    setMemberActionId(memberId);
    try {
      await api.organizations.updateMember(orgId, memberId, { role: nextRole });
      await refreshMembers();
      toast.success("Member role updated");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setMemberActionId(null);
    }
  };

  const handleMemberRemove = async (member: OrgMember) => {
    const label = member.user?.email || member.id;
    if (!confirm(`Remove "${label}" from this organization?`)) {
      return;
    }

    setMemberActionId(member.id);
    try {
      await api.organizations.deleteMember(orgId, member.id);
      await refreshMembers();
      toast.success("Member removed");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setMemberActionId(null);
    }
  };

  const handleInviteCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteSubmitting(true);
    try {
      const invite = await api.organizations.createInvite(orgId, {
        email: inviteEmail,
        role: inviteRole,
      });
      await refreshInvites();
      setInviteEmail("");
      setInviteRole("member");
      if (invite.last_email_error) {
        toast.warning("Invite saved, but email delivery needs attention");
      } else if (invite.email_sent_at) {
        toast.success("Invite created and email sent");
      } else {
        toast.success("Invite created. Email delivery is disabled by config");
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setInviteSubmitting(false);
    }
  };

  const handleInviteDelete = async (invite: OrgInvite) => {
    if (!confirm(`Revoke pending invite for "${invite.email}"?`)) {
      return;
    }

    setInviteActionId(invite.id);
    try {
      await api.organizations.deleteInvite(orgId, invite.id);
      await refreshInvites();
      toast.success("Invite revoked");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setInviteActionId(null);
    }
  };

  const handleInviteResend = async (invite: OrgInvite) => {
    setInviteActionId(invite.id);
    try {
      const updatedInvite = await api.organizations.resendInvite(
        orgId,
        invite.id
      );
      await refreshInvites();
      if (updatedInvite.last_email_error) {
        toast.warning("Invite resend failed");
      } else {
        toast.success("Invite email resent");
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setInviteActionId(null);
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
      <Card>
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Users className="h-5 w-5" />
              Organization Members
            </CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Add existing ConfigHub users so they can access this organization.
            </p>
          </div>
          <Badge variant={isOrgAdmin ? "default" : "outline"}>
            {isOrgAdmin ? "Admin access" : "Member access"}
          </Badge>
        </CardHeader>
        <CardContent className="space-y-6">
          {isOrgAdmin ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <form
                onSubmit={handleAddMember}
                className="grid gap-4 rounded-xl border border-border/70 bg-muted/20 p-4"
              >
                <div>
                  <h3 className="font-semibold">Add Existing User</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Use this when the teammate already has a ConfigHub account.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="member-email">User email</Label>
                  <Input
                    id="member-email"
                    type="email"
                    placeholder="teammate@example.com"
                    value={memberEmail}
                    onChange={(e) => setMemberEmail(e.target.value)}
                    required
                    disabled={memberSubmitting}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="member-role">Role</Label>
                  <Select value={memberRole} onValueChange={handleRoleChange}>
                    <SelectTrigger
                      id="member-role"
                      className="h-9 w-full"
                      disabled={memberSubmitting}
                    >
                      <span className="truncate">{formatRole(memberRole)}</span>
                    </SelectTrigger>
                    <SelectContent align="start">
                      <SelectItem value="member">Member</SelectItem>
                      <SelectItem value="billing_manager">
                        Billing Manager
                      </SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={memberSubmitting}
                >
                  {memberSubmitting ? "Adding..." : "Add Member"}
                </Button>
              </form>

              {inviteEmailsEnabled ? (
                <form
                  onSubmit={handleInviteCreate}
                  className="grid gap-4 rounded-xl border border-border/70 bg-muted/20 p-4"
                >
                  <div>
                    <h3 className="font-semibold">Invite New User</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Create a pending invite that will be accepted
                      automatically when this email signs up later.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invite-email">Invite email</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      placeholder="future-teammate@example.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                      disabled={inviteSubmitting}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invite-role">Role</Label>
                    <Select
                      value={inviteRole}
                      onValueChange={handleInviteRoleChange}
                    >
                      <SelectTrigger
                        id="invite-role"
                        className="h-9 w-full"
                        disabled={inviteSubmitting}
                      >
                        <span className="truncate">
                          {formatRole(inviteRole)}
                        </span>
                      </SelectTrigger>
                      <SelectContent align="start">
                        <SelectItem value="member">Member</SelectItem>
                        <SelectItem value="billing_manager">
                          Billing Manager
                        </SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={inviteSubmitting}
                  >
                    {inviteSubmitting ? "Creating invite..." : "Create Invite"}
                  </Button>
                </form>
              ) : null}
            </div>
          ) : (
            <div className="rounded-xl border border-border/70 bg-muted/20 p-4 text-sm text-muted-foreground">
              Only organization admins can add members.
            </div>
          )}

          {membersLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : members.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 p-6 text-sm text-muted-foreground">
              No members found for this organization yet.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  {isOrgAdmin ? <TableHead>Actions</TableHead> : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <span>{member.user?.name || "Unknown user"}</span>
                        {member.user_id === user?.id ? (
                          <Badge variant="secondary">You</Badge>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      {member.user?.email || "Unknown email"}
                    </TableCell>
                    <TableCell>
                      {isOrgAdmin ? (
                        <Select
                          value={member.role}
                          onValueChange={(nextRole) =>
                            handleMemberRoleUpdate(
                              member.id,
                              nextRole,
                              member.role
                            )
                          }
                          disabled={
                            memberActionId === member.id ||
                            (member.role === "admin" && adminCount === 1)
                          }
                        >
                          <SelectTrigger className="h-9 w-full min-w-[170px]">
                            <span className="truncate">
                              {formatRole(member.role)}
                            </span>
                          </SelectTrigger>
                          <SelectContent align="start">
                            <SelectItem value="member">Member</SelectItem>
                            <SelectItem value="billing_manager">
                              Billing Manager
                            </SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <Badge variant="outline">
                          {formatRole(member.role)}
                        </Badge>
                      )}
                    </TableCell>
                    {isOrgAdmin ? (
                      <TableCell>
                        <Button
                          type="button"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          disabled={
                            memberActionId === member.id ||
                            (member.role === "admin" && adminCount === 1)
                          }
                          onClick={() => handleMemberRemove(member)}
                        >
                          Remove
                        </Button>
                      </TableCell>
                    ) : null}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {isOrgAdmin && (inviteEmailsEnabled || invites.length > 0) ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Pending Invites</CardTitle>
            <p className="text-sm text-muted-foreground">
              {inviteEmailsEnabled
                ? "Invites are matched by email and accepted automatically after that person signs up or logs in."
                : "Invite creation is disabled by configuration. Existing pending invites are shown here so they can still be reviewed or revoked."}
            </p>
          </CardHeader>
          <CardContent>
            {invitesLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            ) : invites.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/70 p-6 text-sm text-muted-foreground">
                No pending invites right now.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Delivery</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invites.map((invite) => (
                    <TableRow key={invite.id}>
                      <TableCell className="font-medium">
                        {invite.email}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {formatRole(invite.role)}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[320px]">
                        {invite.last_email_error ? (
                          <div className="space-y-1">
                            <Badge variant="secondary">Email not sent</Badge>
                            <p className="text-xs text-muted-foreground">
                              {invite.last_email_error}
                            </p>
                          </div>
                        ) : invite.email_sent_at ? (
                          <div className="space-y-1">
                            <Badge>Sent</Badge>
                            <p className="text-xs text-muted-foreground">
                              {new Date(invite.email_sent_at).toLocaleString()}
                            </p>
                          </div>
                        ) : (
                          <Badge variant="secondary">Delivery disabled</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {new Date(invite.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          {inviteEmailsEnabled ? (
                            <Button
                              type="button"
                              variant="ghost"
                              disabled={inviteActionId === invite.id}
                              onClick={() => handleInviteResend(invite)}
                            >
                              Resend
                            </Button>
                          ) : null}
                          <Button
                            type="button"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            disabled={inviteActionId === invite.id}
                            onClick={() => handleInviteDelete(invite)}
                          >
                            Revoke
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Products</h1>
          <p className="text-muted-foreground">
            Manage products in this organization
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Product
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Product</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="My Product"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Optional description"
                />
              </div>
              <Button type="submit" className="w-full">
                Create
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {products.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Package className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              No products yet. Create your first one!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <Card
              key={product.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => router.push(`/dashboard/${orgId}/${product.id}`)}
            >
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">{product.name}</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(product.id, product.name);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                {product.description && (
                  <p className="text-sm text-muted-foreground mb-1">
                    {product.description}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Created {new Date(product.created_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

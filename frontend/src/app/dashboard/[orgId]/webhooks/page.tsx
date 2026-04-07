"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
import { Plus, Trash2, Webhook } from "lucide-react";

export default function WebhooksPage() {
  const { orgId } = useParams() as { orgId: string };
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [deliveriesByWebhook, setDeliveriesByWebhook] = useState<
    Record<string, WebhookDeliveryAttempt[]>
  >({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [signingSecret, setSigningSecret] = useState("");
  const [saving, setSaving] = useState(false);
  const selectedProductName =
    products.find((product) => product.id === selectedProduct)?.name ||
    (products.length === 0 ? "No products" : "Select product");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const orgProducts = await api.products.list(orgId);
        if (cancelled) return;
        setProducts(orgProducts);
        setSelectedProduct((current) => current || orgProducts[0]?.id || "");
      } catch (err: any) {
        if (!cancelled) {
          toast.error(err.message);
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  useEffect(() => {
    if (!selectedProduct) {
      setWebhooks([]);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const data = await api.webhooks.list(selectedProduct);
        const deliveries = await Promise.all(
          data.map(async (webhook) => [
            webhook.id,
            await api.webhooks.deliveries(selectedProduct, webhook.id, 5),
          ])
        );
        if (!cancelled) {
          setWebhooks(data);
          setDeliveriesByWebhook(Object.fromEntries(deliveries));
        }
      } catch (err: any) {
        if (!cancelled) {
          toast.error(err.message);
          setWebhooks([]);
          setDeliveriesByWebhook({});
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedProduct]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProduct) return;
    try {
      setSaving(true);
      await api.webhooks.create(selectedProduct, {
        url,
        signing_secret: signingSecret || undefined,
        enabled: true,
      });
      setUrl("");
      setSigningSecret("");
      setDialogOpen(false);
      toast.success("Webhook created");
      fetchWebhooks();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!selectedProduct) return;
    if (!confirm("Delete this webhook?")) return;
    try {
      await api.webhooks.delete(selectedProduct, id);
      toast.success("Deleted");
      const data = await api.webhooks.list(selectedProduct);
      setWebhooks(data);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const fetchWebhooks = async () => {
    if (!selectedProduct) {
      setWebhooks([]);
      setDeliveriesByWebhook({});
      return;
    }
    const data = await api.webhooks.list(selectedProduct);
    const deliveries = await Promise.all(
      data.map(async (webhook) => [
        webhook.id,
        await api.webhooks.deliveries(selectedProduct, webhook.id, 5),
      ])
    );
    setWebhooks(data);
    setDeliveriesByWebhook(Object.fromEntries(deliveries));
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
          <h1 className="text-2xl font-bold">Webhooks</h1>
          <p className="text-muted-foreground">
            Receive notifications when changes happen
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={selectedProduct}
            onValueChange={(value) => setSelectedProduct(value ?? "")}
            disabled={products.length === 0}
          >
            <SelectTrigger className="w-[220px]">
              <span className="truncate">{selectedProductName}</span>
            </SelectTrigger>
            <SelectContent>
              {products.map((product) => (
                <SelectItem key={product.id} value={product.id}>
                  {product.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger>
              <Button disabled={!selectedProduct}>
                <Plus className="mr-2 h-4 w-4" />
                New Webhook
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Webhook</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-2">
                  <Label>URL</Label>
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/webhook"
                    type="url"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Signing Secret</Label>
                  <Input
                    value={signingSecret}
                    onChange={(e) => setSigningSecret(e.target.value)}
                    placeholder="Leave blank to auto-generate"
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  This webhook applies to the currently selected product and
                  signs every request with `X-ConfigHub-Signature-256`.
                </p>
                <Button type="submit" className="w-full" disabled={saving}>
                  {saving ? "Creating..." : "Create"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {!selectedProduct ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Webhook className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              Create a product first to manage webhooks.
            </p>
          </CardContent>
        </Card>
      ) : webhooks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Webhook className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">No webhooks configured.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>URL</TableHead>
                <TableHead>Signing</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Recent Deliveries</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {webhooks.map((wh) => (
                <TableRow key={wh.id}>
                  <TableCell className="font-mono text-sm max-w-[300px] truncate">
                    {wh.url}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    <span title={wh.signing_secret}>
                      {`${wh.signing_secret.slice(0, 10)}...`}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {wh.config_id ? (
                        <Badge variant="outline" className="text-xs">
                          Config {wh.config_id.slice(0, 8)}
                        </Badge>
                      ) : (
                        <Badge variant="secondary">All configs</Badge>
                      )}
                      {wh.environment_id ? (
                        <Badge variant="outline" className="text-xs">
                          Env {wh.environment_id.slice(0, 8)}
                        </Badge>
                      ) : (
                        <Badge variant="secondary">All envs</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={wh.enabled ? "default" : "secondary"}>
                      {wh.enabled ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="space-y-2">
                      {(deliveriesByWebhook[wh.id] || []).length === 0 ? (
                        <span className="text-sm text-muted-foreground">
                          No deliveries yet
                        </span>
                      ) : (
                        (deliveriesByWebhook[wh.id] || []).map((attempt) => (
                          <div key={attempt.id} className="text-xs">
                            <Badge
                              variant={
                                attempt.delivered_at ? "default" : "secondary"
                              }
                              className="mr-2"
                            >
                              {attempt.delivered_at ? "Delivered" : "Failed"}
                            </Badge>
                            <span className="text-muted-foreground">
                              {attempt.event} · try {attempt.attempt_number}
                              {attempt.status_code
                                ? ` · HTTP ${attempt.status_code}`
                                : ""}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(wh.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDelete(wh.id)}
                    >
                      <Trash2 className="h-4 w-4" />
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

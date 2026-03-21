"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Layers, Plus, Trash2 } from "lucide-react";

export default function ConfigsPage() {
  const { orgId, productId } = useParams() as { orgId: string; productId: string };
  const [configs, setConfigs] = useState<Config[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const router = useRouter();

  const fetchConfigs = async () => {
    try {
      const data = await api.configs.list(productId);
      setConfigs(data);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConfigs(); }, [productId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.configs.create(productId, { name: newName, description: newDesc || undefined });
      setNewName(""); setNewDesc(""); setDialogOpen(false);
      toast.success("Config created");
      fetchConfigs();
    } catch (err: any) { toast.error(err.message); }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete config "${name}"?`)) return;
    try {
      await api.configs.delete(productId, id);
      toast.success("Config deleted");
      fetchConfigs();
    } catch (err: any) { toast.error(err.message); }
  };

  if (loading) return <div className="flex items-center justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Configs</h1>
          <p className="text-muted-foreground">Feature flag configurations for this product</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger >
            <Button><Plus className="mr-2 h-4 w-4" />New Config</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Config</DialogTitle></DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Main Config" required />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Optional description" />
              </div>
              <Button type="submit" className="w-full">Create</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {configs.length === 0 ? (
        <Card><CardContent className="flex flex-col items-center justify-center py-12">
          <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <p className="text-muted-foreground">No configs yet. Create your first one!</p>
        </CardContent></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {configs.map((cfg) => (
            <Card key={cfg.id} className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => router.push(`/dashboard/${orgId}/${productId}/${cfg.id}`)}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">{cfg.name}</CardTitle>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); handleDelete(cfg.id, cfg.name); }}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                {cfg.description && <p className="text-sm text-muted-foreground mb-1">{cfg.description}</p>}
                <p className="text-xs text-muted-foreground">Created {new Date(cfg.created_at).toLocaleDateString()}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}


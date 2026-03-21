"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Trash2, Settings } from "lucide-react";

export default function EnvironmentsPage() {
  const { productId } = useParams() as { productId: string };
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#4CAF50");
  const [dialogOpen, setDialogOpen] = useState(false);

  const fetchEnvs = async () => {
    try { setEnvs(await api.environments.list(productId)); }
    catch (err: any) { toast.error(err.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchEnvs(); }, [productId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.environments.create(productId, { name: newName, color: newColor });
      setNewName(""); setNewColor("#4CAF50"); setDialogOpen(false);
      toast.success("Environment created");
      fetchEnvs();
    } catch (err: any) { toast.error(err.message); }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete environment "${name}"?`)) return;
    try {
      await api.environments.delete(productId, id);
      toast.success("Environment deleted");
      fetchEnvs();
    } catch (err: any) { toast.error(err.message); }
  };

  if (loading) return <div className="flex items-center justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Environments</h1>
          <p className="text-muted-foreground">Manage deployment environments</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger >
            <Button><Plus className="mr-2 h-4 w-4" />New Environment</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Environment</DialogTitle></DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Production" required />
              </div>
              <div className="space-y-2">
                <Label>Color</Label>
                <div className="flex gap-2 items-center">
                  <input type="color" value={newColor} onChange={(e) => setNewColor(e.target.value)} className="h-10 w-10 rounded border cursor-pointer" />
                  <Input value={newColor} onChange={(e) => setNewColor(e.target.value)} className="flex-1" />
                </div>
              </div>
              <Button type="submit" className="w-full">Create</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {envs.length === 0 ? (
        <Card><CardContent className="flex flex-col items-center justify-center py-12">
          <Settings className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <p className="text-muted-foreground">No environments yet.</p>
        </CardContent></Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Color</TableHead>
                <TableHead>Order</TableHead>
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {envs.map((env) => (
                <TableRow key={env.id}>
                  <TableCell className="font-medium">{env.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="gap-1.5">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: env.color }} />
                      {env.color}
                    </Badge>
                  </TableCell>
                  <TableCell>{env.order}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => handleDelete(env.id, env.name)}>
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


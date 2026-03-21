"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, Trash2, Users } from "lucide-react";

const COMPARATORS = [
  { value: "equals", label: "equals" },
  { value: "notEquals", label: "not equals" },
  { value: "contains", label: "contains" },
  { value: "notContains", label: "not contains" },
  { value: "isOneOf", label: "is one of" },
  { value: "isNotOneOf", label: "is not one of" },
  { value: "numberEquals", label: "= (num)" },
  { value: "numberLess", label: "< (num)" },
  { value: "numberGreater", label: "> (num)" },
  { value: "regexMatch", label: "regex match" },
];

interface EditSegCond {
  attribute: string;
  comparator: string;
  comparison_value: string;
}

export default function SegmentsPage() {
  const { productId } = useParams() as { productId: string };
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [conditions, setConditions] = useState<EditSegCond[]>([
    { attribute: "", comparator: "equals", comparison_value: "" },
  ]);

  useEffect(() => {
    let cancelled = false;
    const loadSegments = async () => {
      try {
        const data = await api.segments.list(productId);
        if (!cancelled) setSegments(data);
      } catch (err: any) {
        if (!cancelled) toast.error(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadSegments();
    return () => {
      cancelled = true;
    };
  }, [productId]);

  const resetForm = () => {
    setName("");
    setDescription("");
    setConditions([
      { attribute: "", comparator: "equals", comparison_value: "" },
    ]);
    setEditId(null);
  };

  const openCreate = () => {
    resetForm();
    setDialogOpen(true);
  };
  const openEdit = (seg: Segment) => {
    setEditId(seg.id);
    setName(seg.name);
    setDescription(seg.description || "");
    setConditions(
      seg.conditions.map((c) => ({
        attribute: c.attribute,
        comparator: c.comparator,
        comparison_value:
          c.comparison_value?.v !== undefined
            ? String(c.comparison_value.v)
            : "",
      }))
    );
    setDialogOpen(true);
  };

  const addCond = () =>
    setConditions([
      ...conditions,
      { attribute: "", comparator: "equals", comparison_value: "" },
    ]);
  const removeCond = (i: number) =>
    setConditions(conditions.filter((_, idx) => idx !== i));
  const updateCond = (i: number, f: keyof EditSegCond, v: string | null) => {
    if (v === null) return;
    const u = [...conditions];
    u[i] = { ...u[i], [f]: v };
    setConditions(u);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const data: SegmentCreate = {
      name,
      description: description || undefined,
      conditions: conditions.map((c) => ({
        attribute: c.attribute,
        comparator: c.comparator,
        comparison_value: { v: c.comparison_value },
      })),
    };
    try {
      if (editId) {
        await api.segments.update(productId, editId, data);
        toast.success("Segment updated");
      } else {
        await api.segments.create(productId, data);
        toast.success("Segment created");
      }
      const refreshed = await api.segments.list(productId);
      setSegments(refreshed);
      setDialogOpen(false);
      resetForm();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleDelete = async (id: string, segName: string) => {
    if (!confirm(`Delete segment "${segName}"?`)) return;
    try {
      await api.segments.delete(productId, id);
      const refreshed = await api.segments.list(productId);
      setSegments(refreshed);
      toast.success("Deleted");
    } catch (err: any) {
      toast.error(err.message);
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
          <h1 className="text-2xl font-bold">Segments</h1>
          <p className="text-muted-foreground">
            Reusable groups of users for targeting
          </p>
        </div>
        <Dialog
          open={dialogOpen}
          onOpenChange={(o) => {
            setDialogOpen(o);
            if (!o) resetForm();
          }}
        >
          <DialogTrigger>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              New Segment
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editId ? "Edit" : "Create"} Segment</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Conditions</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addCond}
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    Add
                  </Button>
                </div>
                {conditions.map((c, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      className="flex-1"
                      placeholder="attribute"
                      value={c.attribute}
                      onChange={(e) =>
                        updateCond(i, "attribute", e.target.value)
                      }
                    />
                    <Select
                      value={c.comparator}
                      onValueChange={(v) => updateCond(i, "comparator", v)}
                    >
                      <SelectTrigger className="w-[150px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COMPARATORS.map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      className="flex-1"
                      placeholder="value"
                      value={c.comparison_value}
                      onChange={(e) =>
                        updateCond(i, "comparison_value", e.target.value)
                      }
                    />
                    {conditions.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => removeCond(i)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              <Button type="submit" className="w-full">
                {editId ? "Update" : "Create"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {segments.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Users className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">No segments yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {segments.map((seg) => (
            <Card
              key={seg.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => openEdit(seg)}
            >
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <CardTitle className="text-base">{seg.name}</CardTitle>
                  {seg.description && (
                    <CardDescription>{seg.description}</CardDescription>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(seg.id, seg.name);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {seg.conditions.map((c, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs"
                    >
                      <span className="font-medium">{c.attribute}</span>&nbsp;
                      {c.comparator}&nbsp;
                      <span className="text-muted-foreground">
                        {String(c.comparison_value?.v ?? "")}
                      </span>
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

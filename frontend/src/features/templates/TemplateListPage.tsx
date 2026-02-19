import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient, useQueries } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import {
  Copy,
  LayoutTemplate,
  Lock,
  MoreHorizontal,
  Plus,
  Trash2,
} from "lucide-react";

import { PageHeader, EmptyState } from "@/components/shared";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import {
  cloneTemplate,
  createTemplate,
  deleteTemplate,
  getTemplate,
  listTemplates,
  type DeviceTemplate,
} from "@/services/api/templates";
import { getErrorMessage } from "@/lib/errors";

const categoryLabels: Record<string, string> = {
  gateway: "Gateway",
  edge_device: "Edge Device",
  standalone_sensor: "Standalone Sensor",
  controller: "Controller",
  expansion_module: "Expansion Module",
};

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export default function TemplateListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [category, setCategory] = useState<string>("all");
  const [source, setSource] = useState<string>("all");
  const [search, setSearch] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createCategory, setCreateCategory] = useState<string>("gateway");

  const [deleting, setDeleting] = useState<DeviceTemplate | null>(null);

  const { data: templates, isLoading, error } = useQuery({
    queryKey: ["templates", { category, source, search }],
    queryFn: () =>
      listTemplates({
        category: category === "all" ? undefined : category,
        source: source === "all" ? undefined : source,
        search: search.trim() ? search.trim() : undefined,
      }),
  });

  // Count columns need full template detail. Fetch details for the first page worth of templates.
  const templatesForCounts = (templates ?? []).slice(0, 50);
  const detailQueries = useQueries({
    queries: templatesForCounts.map((t) => ({
      queryKey: ["templates", t.id],
      queryFn: () => getTemplate(t.id),
      staleTime: 30_000,
    })),
  });
  const countsById = useMemo(() => {
    const map = new Map<number, { metrics: number; slots: number }>();
    for (const q of detailQueries) {
      const d = q.data;
      if (d) map.set(d.id, { metrics: d.metrics.length, slots: d.slots.length });
    }
    return map;
  }, [detailQueries]);

  const createMutation = useMutation({
    mutationFn: createTemplate,
    onSuccess: async (created) => {
      toast.success("Template added");
      setCreateOpen(false);
      setCreateName("");
      setCreateSlug("");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate(`/templates/${created.id}`);
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err) || "Failed to add template");
    },
  });

  const cloneMutation = useMutation({
    mutationFn: (templateId: number) => cloneTemplate(templateId),
    onSuccess: async (cloned) => {
      toast.success("Template cloned");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate(`/templates/${cloned.id}`);
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err) || "Failed to clone template");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: number) => deleteTemplate(templateId),
    onSuccess: async () => {
      toast.success("Template deleted");
      setDeleting(null);
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err) || "Failed to delete template");
    },
  });

  const rows = useMemo(() => templates ?? [], [templates]);

  const columns = useMemo<ColumnDef<DeviceTemplate>[]>(() => {
    return [
      {
        accessorKey: "name",
        header: "Name",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <span className="font-medium">{row.original.name}</span>
            {row.original.is_locked ? <Lock className="h-3.5 w-3.5 text-muted-foreground" /> : null}
          </div>
        ),
      },
      {
        accessorKey: "category",
        header: "Category",
        cell: ({ row }) => categoryLabels[row.original.category] ?? row.original.category,
      },
      {
        id: "source",
        header: "Source",
        cell: ({ row }) =>
          row.original.source === "system" ? (
            <Badge variant="secondary" className="gap-1">
              <Lock className="h-3.5 w-3.5" />
              System
            </Badge>
          ) : (
            <Badge>Custom</Badge>
          ),
      },
      {
        accessorKey: "manufacturer",
        header: "Manufacturer",
        cell: ({ row }) => row.original.manufacturer ?? "—",
      },
      {
        accessorKey: "model",
        header: "Model",
        cell: ({ row }) => row.original.model ?? "—",
      },
      {
        id: "metrics_count",
        header: "Metrics",
        cell: ({ row }) => {
          const c = countsById.get(row.original.id);
          return c ? String(c.metrics) : "—";
        },
      },
      {
        id: "slots_count",
        header: "Slots",
        cell: ({ row }) => {
          const c = countsById.get(row.original.id);
          return c ? String(c.slots) : "—";
        },
      },
      {
        id: "actions",
        header: () => <span className="text-right">Actions</span>,
        enableSorting: false,
        cell: ({ row }) => {
          const t = row.original;
          const canClone = t.source === "system";
          const canDelete = t.source === "tenant" && !t.is_locked;
          return (
            <div className="flex justify-end">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={(e) => e.stopPropagation()}>
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                  {canClone ? (
                    <DropdownMenuItem onClick={() => cloneMutation.mutate(t.id)}>
                      <Copy className="mr-2 h-4 w-4" />
                      Clone
                    </DropdownMenuItem>
                  ) : null}
                  <DropdownMenuItem onClick={() => navigate(`/templates/${t.id}`)}>
                    <LayoutTemplate className="mr-2 h-4 w-4" />
                    View
                  </DropdownMenuItem>
                  {canDelete ? (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => setDeleting(t)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </>
                  ) : null}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        },
      },
    ];
  }, [cloneMutation, countsById, navigate]);

  const description = isLoading ? "Loading..." : `${rows.length} templates`;

  const emptyState = (
    <EmptyState
      title="No templates found"
      description="Try adjusting your filters, or add a new template."
      icon={<LayoutTemplate className="h-8 w-8" />}
      action={
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1 h-4 w-4" />
          Add Template
        </Button>
      }
    />
  );

  const canSubmitCreate = createName.trim().length > 0 && createSlug.trim().length > 0;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Device Templates"
        description={description}
        action={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Add Template
          </Button>
        }
      />

      {error ? (
        <div className="text-destructive">Failed to load templates: {getErrorMessage(error)}</div>
      ) : (
        <>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <div className="flex gap-2">
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="gateway">Gateway</SelectItem>
                  <SelectItem value="edge_device">Edge Device</SelectItem>
                  <SelectItem value="standalone_sensor">Standalone Sensor</SelectItem>
                  <SelectItem value="controller">Controller</SelectItem>
                  <SelectItem value="expansion_module">Expansion Module</SelectItem>
                </SelectContent>
              </Select>

              <Select value={source} onValueChange={setSource}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                  <SelectItem value="tenant">Tenant</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Input
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="md:max-w-[320px]"
            />
          </div>

          <DataTable
            columns={columns}
            data={rows}
            isLoading={isLoading}
            emptyState={emptyState}
            onRowClick={(t) => navigate(`/templates/${t.id}`)}
          />
        </>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Template</DialogTitle>
            <DialogDescription>Create a tenant-owned device template.</DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                value={createName}
                onChange={(e) => {
                  const v = e.target.value;
                  setCreateName(v);
                  if (!createSlug || createSlug === slugify(createName)) {
                    setCreateSlug(slugify(v));
                  }
                }}
                placeholder="My Gateway v1"
              />
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium">Slug</label>
              <Input
                value={createSlug}
                onChange={(e) => setCreateSlug(e.target.value)}
                placeholder="my-gateway-v1"
              />
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium">Category</label>
              <Select value={createCategory} onValueChange={setCreateCategory}>
                <SelectTrigger>
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gateway">Gateway</SelectItem>
                  <SelectItem value="edge_device">Edge Device</SelectItem>
                  <SelectItem value="standalone_sensor">Standalone Sensor</SelectItem>
                  <SelectItem value="controller">Controller</SelectItem>
                  <SelectItem value="expansion_module">Expansion Module</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateOpen(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                createMutation.mutate({
                  name: createName.trim(),
                  slug: createSlug.trim(),
                  category: createCategory,
                })
              }
              disabled={!canSubmitCreate || createMutation.isPending}
            >
              <Plus className="mr-1 h-4 w-4" />
              Add Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleting} onOpenChange={(open) => (!open ? setDeleting(null) : null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete template?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleting ? (
                <>
                  This will permanently delete <span className="font-medium">{deleting.name}</span>.
                </>
              ) : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleting(null)} disabled={deleteMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
              disabled={!deleting || deleteMutation.isPending}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}


import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import {
  Copy,
  Lock,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";

import { PageHeader, EmptyState } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
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
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  cloneTemplate,
  createTemplateCommand,
  createTemplateMetric,
  createTemplateSlot,
  deleteTemplateCommand,
  deleteTemplateMetric,
  deleteTemplateSlot,
  getTemplate,
  listTemplates,
  updateTemplate,
  updateTemplateCommand,
  updateTemplateMetric,
  updateTemplateSlot,
  type TemplateCommand,
  type TemplateCommandPayload,
  type TemplateDetail,
  type TemplateMetric,
  type TemplateMetricPayload,
  type TemplateSlot,
  type TemplateSlotPayload,
  type TemplateUpdatePayload,
} from "@/services/api/templates";
import { getErrorMessage } from "@/lib/errors";

const categoryLabels: Record<string, string> = {
  gateway: "Gateway",
  edge_device: "Edge Device",
  standalone_sensor: "Standalone Sensor",
  controller: "Controller",
  expansion_module: "Expansion Module",
};

function safeJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return "{}";
  }
}

function parseJsonObject(text: string): Record<string, unknown> | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("JSON must be an object");
  }
  return parsed as Record<string, unknown>;
}

export default function TemplateDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { templateId } = useParams<{ templateId: string }>();
  const id = Number(templateId);

  const { data: template, isLoading, error } = useQuery({
    queryKey: ["templates", id],
    queryFn: () => getTemplate(id),
    enabled: Number.isFinite(id),
  });

  const { data: allTemplates } = useQuery({
    queryKey: ["templates", "lookup"],
    queryFn: () => listTemplates(),
  });

  const templateNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const t of allTemplates ?? []) map.set(t.id, t.name);
    return map;
  }, [allTemplates]);

  const expansionModules = useMemo(() => {
    return (allTemplates ?? []).filter((t) => t.category === "expansion_module");
  }, [allTemplates]);

  const editable = !!template && template.source === "tenant" && !template.is_locked;

  // ── Clone banner action ────────────────────────────────

  const cloneMutation = useMutation({
    mutationFn: (templateIdToClone: number) => cloneTemplate(templateIdToClone),
    onSuccess: async (cloned) => {
      toast.success("Template cloned");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate(`/templates/${cloned.id}`);
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to clone template"),
  });

  // ── Template edit (overview) ────────────────────────────

  const [editOpen, setEditOpen] = useState(false);
  const [editDraft, setEditDraft] = useState<TemplateUpdatePayload>({});
  const [editTransportDefaults, setEditTransportDefaults] = useState<string>("{}");
  const [editMetadata, setEditMetadata] = useState<string>("{}");

  function openEdit(tpl: TemplateDetail) {
    setEditDraft({
      name: tpl.name,
      description: tpl.description ?? undefined,
      category: tpl.category,
      manufacturer: tpl.manufacturer ?? undefined,
      model: tpl.model ?? undefined,
      firmware_version_pattern: tpl.firmware_version_pattern ?? undefined,
      image_url: tpl.image_url ?? undefined,
    });
    setEditTransportDefaults(safeJsonStringify(tpl.transport_defaults ?? {}));
    setEditMetadata(safeJsonStringify(tpl.metadata ?? {}));
    setEditOpen(true);
  }

  const updateTemplateMutation = useMutation({
    mutationFn: (payload: { templateIdToUpdate: number; data: TemplateUpdatePayload }) =>
      updateTemplate(payload.templateIdToUpdate, payload.data),
    onSuccess: async () => {
      toast.success("Template updated");
      setEditOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to update template"),
  });

  // ── Metrics CRUD ────────────────────────────────────────

  const [metricOpen, setMetricOpen] = useState(false);
  const [editingMetric, setEditingMetric] = useState<TemplateMetric | null>(null);
  const [metricDraft, setMetricDraft] = useState<TemplateMetricPayload>({
    metric_key: "",
    display_name: "",
    data_type: "float",
    unit: "",
    min_value: undefined,
    max_value: undefined,
    precision_digits: 2,
    is_required: false,
    description: "",
    enum_values: [],
    sort_order: 0,
  });

  function openAddMetric() {
    setEditingMetric(null);
    setMetricDraft({
      metric_key: "",
      display_name: "",
      data_type: "float",
      unit: "",
      min_value: undefined,
      max_value: undefined,
      precision_digits: 2,
      is_required: false,
      description: "",
      enum_values: [],
      sort_order: 0,
    });
    setMetricOpen(true);
  }

  function openEditMetric(m: TemplateMetric) {
    setEditingMetric(m);
    setMetricDraft({
      metric_key: m.metric_key,
      display_name: m.display_name,
      data_type: m.data_type,
      unit: m.unit ?? "",
      min_value: m.min_value ?? undefined,
      max_value: m.max_value ?? undefined,
      precision_digits: m.precision_digits,
      is_required: m.is_required,
      description: m.description ?? "",
      enum_values: m.enum_values ?? [],
      sort_order: m.sort_order,
    });
    setMetricOpen(true);
  }

  const createMetricMutation = useMutation({
    mutationFn: (payload: { templateIdForMetric: number; data: TemplateMetricPayload }) =>
      createTemplateMetric(payload.templateIdForMetric, payload.data),
    onSuccess: async () => {
      toast.success("Metric added");
      setMetricOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to add metric"),
  });

  const updateMetricMutation = useMutation({
    mutationFn: (payload: {
      templateIdForMetric: number;
      metricId: number;
      data: Partial<TemplateMetricPayload>;
    }) => updateTemplateMetric(payload.templateIdForMetric, payload.metricId, payload.data),
    onSuccess: async () => {
      toast.success("Metric updated");
      setMetricOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to update metric"),
  });

  const deleteMetricMutation = useMutation({
    mutationFn: (payload: { templateIdForMetric: number; metricId: number }) =>
      deleteTemplateMetric(payload.templateIdForMetric, payload.metricId),
    onSuccess: async () => {
      toast.success("Metric deleted");
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to delete metric"),
  });

  const [deletingMetric, setDeletingMetric] = useState<TemplateMetric | null>(null);

  // ── Commands CRUD ───────────────────────────────────────

  const [commandOpen, setCommandOpen] = useState(false);
  const [editingCommand, setEditingCommand] = useState<TemplateCommand | null>(null);
  const [commandDraft, setCommandDraft] = useState<TemplateCommandPayload>({
    command_key: "",
    display_name: "",
    description: "",
    parameters_schema: {},
    response_schema: {},
    sort_order: 0,
  });
  const [commandParametersJson, setCommandParametersJson] = useState("{}");
  const [commandResponseJson, setCommandResponseJson] = useState("{}");

  function openAddCommand() {
    setEditingCommand(null);
    setCommandDraft({
      command_key: "",
      display_name: "",
      description: "",
      parameters_schema: {},
      response_schema: {},
      sort_order: 0,
    });
    setCommandParametersJson("{}");
    setCommandResponseJson("{}");
    setCommandOpen(true);
  }

  function openEditCommand(c: TemplateCommand) {
    setEditingCommand(c);
    setCommandDraft({
      command_key: c.command_key,
      display_name: c.display_name,
      description: c.description ?? "",
      parameters_schema: c.parameters_schema ?? {},
      response_schema: c.response_schema ?? {},
      sort_order: c.sort_order,
    });
    setCommandParametersJson(safeJsonStringify(c.parameters_schema ?? {}));
    setCommandResponseJson(safeJsonStringify(c.response_schema ?? {}));
    setCommandOpen(true);
  }

  const createCommandMutation = useMutation({
    mutationFn: (payload: { templateIdForCommand: number; data: TemplateCommandPayload }) =>
      createTemplateCommand(payload.templateIdForCommand, payload.data),
    onSuccess: async () => {
      toast.success("Command added");
      setCommandOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to add command"),
  });

  const updateCommandMutation = useMutation({
    mutationFn: (payload: {
      templateIdForCommand: number;
      commandId: number;
      data: Partial<TemplateCommandPayload>;
    }) => updateTemplateCommand(payload.templateIdForCommand, payload.commandId, payload.data),
    onSuccess: async () => {
      toast.success("Command updated");
      setCommandOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to update command"),
  });

  const deleteCommandMutation = useMutation({
    mutationFn: (payload: { templateIdForCommand: number; commandId: number }) =>
      deleteTemplateCommand(payload.templateIdForCommand, payload.commandId),
    onSuccess: async () => {
      toast.success("Command deleted");
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to delete command"),
  });

  const [deletingCommand, setDeletingCommand] = useState<TemplateCommand | null>(null);

  // ── Slots CRUD ─────────────────────────────────────────

  const [slotOpen, setSlotOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState<TemplateSlot | null>(null);
  const [slotDraft, setSlotDraft] = useState<TemplateSlotPayload>({
    slot_key: "",
    display_name: "",
    slot_type: "expansion",
    interface_type: "analog",
    max_devices: 1,
    compatible_templates: [],
    is_required: false,
    description: "",
    sort_order: 0,
  });

  function openAddSlot() {
    setEditingSlot(null);
    setSlotDraft({
      slot_key: "",
      display_name: "",
      slot_type: "expansion",
      interface_type: "analog",
      max_devices: 1,
      compatible_templates: [],
      is_required: false,
      description: "",
      sort_order: 0,
    });
    setSlotOpen(true);
  }

  function openEditSlot(s: TemplateSlot) {
    setEditingSlot(s);
    setSlotDraft({
      slot_key: s.slot_key,
      display_name: s.display_name,
      slot_type: s.slot_type,
      interface_type: s.interface_type,
      max_devices: s.max_devices ?? undefined,
      compatible_templates: s.compatible_templates ?? [],
      is_required: s.is_required,
      description: s.description ?? "",
      sort_order: s.sort_order,
    });
    setSlotOpen(true);
  }

  const createSlotMutation = useMutation({
    mutationFn: (payload: { templateIdForSlot: number; data: TemplateSlotPayload }) =>
      createTemplateSlot(payload.templateIdForSlot, payload.data),
    onSuccess: async () => {
      toast.success("Slot added");
      setSlotOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to add slot"),
  });

  const updateSlotMutation = useMutation({
    mutationFn: (payload: {
      templateIdForSlot: number;
      slotId: number;
      data: Partial<TemplateSlotPayload>;
    }) => updateTemplateSlot(payload.templateIdForSlot, payload.slotId, payload.data),
    onSuccess: async () => {
      toast.success("Slot updated");
      setSlotOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to update slot"),
  });

  const deleteSlotMutation = useMutation({
    mutationFn: (payload: { templateIdForSlot: number; slotId: number }) =>
      deleteTemplateSlot(payload.templateIdForSlot, payload.slotId),
    onSuccess: async () => {
      toast.success("Slot deleted");
      await queryClient.invalidateQueries({ queryKey: ["templates", id] });
    },
    onError: (err: unknown) => toast.error(getErrorMessage(err) || "Failed to delete slot"),
  });

  const [deletingSlot, setDeletingSlot] = useState<TemplateSlot | null>(null);

  const metricsColumns = useMemo<ColumnDef<TemplateMetric>[]>(() => {
    return [
      { accessorKey: "sort_order", header: "Order" },
      { accessorKey: "metric_key", header: "Metric Key" },
      { accessorKey: "display_name", header: "Display Name" },
      {
        accessorKey: "data_type",
        header: "Type",
        cell: ({ row }) => <Badge variant="secondary">{row.original.data_type}</Badge>,
      },
      { accessorKey: "unit", header: "Unit", cell: ({ row }) => row.original.unit ?? "—" },
      {
        id: "range",
        header: "Range",
        cell: ({ row }) => {
          const { min_value, max_value } = row.original;
          if (min_value == null && max_value == null) return "—";
          return `${min_value ?? "—"} – ${max_value ?? "—"}`;
        },
      },
      {
        accessorKey: "is_required",
        header: "Required",
        cell: ({ row }) => (row.original.is_required ? "Yes" : "No"),
      },
      ...(editable
        ? [
            {
              id: "actions",
              header: () => <span className="text-right">Actions</span>,
              enableSorting: false,
              cell: ({ row }: { row: { original: TemplateMetric } }) => (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" onClick={() => openEditMetric(row.original)}>
                    <Pencil className="mr-1 h-3.5 w-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => setDeletingMetric(row.original)}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Delete
                  </Button>
                </div>
              ),
            } as ColumnDef<TemplateMetric>,
          ]
        : []),
    ];
  }, [editable, id]);

  const commandsColumns = useMemo<ColumnDef<TemplateCommand>[]>(() => {
    return [
      { accessorKey: "sort_order", header: "Order" },
      { accessorKey: "command_key", header: "Command Key" },
      { accessorKey: "display_name", header: "Display Name" },
      {
        accessorKey: "description",
        header: "Description",
        cell: ({ row }) => (row.original.description ? String(row.original.description).slice(0, 60) : "—"),
      },
      ...(editable
        ? [
            {
              id: "actions",
              header: () => <span className="text-right">Actions</span>,
              enableSorting: false,
              cell: ({ row }: { row: { original: TemplateCommand } }) => (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" onClick={() => openEditCommand(row.original)}>
                    <Pencil className="mr-1 h-3.5 w-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => setDeletingCommand(row.original)}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Delete
                  </Button>
                </div>
              ),
            } as ColumnDef<TemplateCommand>,
          ]
        : []),
    ];
  }, [editable, id]);

  const slotsColumns = useMemo<ColumnDef<TemplateSlot>[]>(() => {
    return [
      { accessorKey: "sort_order", header: "Order" },
      { accessorKey: "slot_key", header: "Slot Key" },
      { accessorKey: "display_name", header: "Display Name" },
      {
        accessorKey: "slot_type",
        header: "Type",
        cell: ({ row }) => <Badge variant="secondary">{row.original.slot_type}</Badge>,
      },
      {
        accessorKey: "interface_type",
        header: "Interface",
        cell: ({ row }) => <Badge variant="secondary">{row.original.interface_type}</Badge>,
      },
      {
        accessorKey: "max_devices",
        header: "Max",
        cell: ({ row }) => (row.original.max_devices == null ? "Unlimited" : row.original.max_devices),
      },
      {
        accessorKey: "is_required",
        header: "Required",
        cell: ({ row }) => (row.original.is_required ? "Yes" : "No"),
      },
      {
        id: "compatible",
        header: "Compatible",
        cell: ({ row }) => {
          const ids = row.original.compatible_templates ?? [];
          if (!ids.length) return "—";
          const names = ids
            .map((tid) => templateNameById.get(tid) ?? `#${tid}`)
            .slice(0, 3);
          return ids.length > 3 ? `${names.join(", ")} +${ids.length - 3}` : names.join(", ");
        },
      },
      ...(editable
        ? [
            {
              id: "actions",
              header: () => <span className="text-right">Actions</span>,
              enableSorting: false,
              cell: ({ row }: { row: { original: TemplateSlot } }) => (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" onClick={() => openEditSlot(row.original)}>
                    <Pencil className="mr-1 h-3.5 w-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => setDeletingSlot(row.original)}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Delete
                  </Button>
                </div>
              ),
            } as ColumnDef<TemplateSlot>,
          ]
        : []),
    ];
  }, [editable, id, templateNameById]);

  if (!Number.isFinite(id)) {
    return (
      <div className="space-y-4">
        <PageHeader title="Template" description="Invalid template id" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageHeader title="Template" description="Failed to load" />
        <div className="text-destructive">Failed to load template: {getErrorMessage(error)}</div>
      </div>
    );
  }

  if (isLoading || !template) {
    return (
      <div className="space-y-4">
        <PageHeader title="Template" description="Loading..." />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title={template.name}
        description={`${categoryLabels[template.category] ?? template.category} • ${template.source === "system" ? "System" : "Custom"}`}
        action={
          <div className="flex items-center gap-2">
            {template.is_locked ? (
              <Badge variant="secondary" className="gap-1">
                <Lock className="h-3.5 w-3.5" />
                System
              </Badge>
            ) : (
              <Badge>Custom</Badge>
            )}
            {editable ? (
              <Button variant="outline" onClick={() => openEdit(template)}>
                <Pencil className="mr-1 h-4 w-4" />
                Edit
              </Button>
            ) : null}
          </div>
        }
      />

      {template.is_locked ? (
        <div className="rounded-lg border border-border p-3 bg-muted/30 flex items-center justify-between">
          <div className="text-sm">
            <div className="font-medium">System template</div>
            <div className="text-muted-foreground">
              This template is read-only. Clone it to create a customizable copy.
            </div>
          </div>
          <Button onClick={() => cloneMutation.mutate(template.id)} disabled={cloneMutation.isPending}>
            <Copy className="mr-1 h-4 w-4" />
            Clone Template
          </Button>
        </div>
      ) : null}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics ({template.metrics.length})</TabsTrigger>
          <TabsTrigger value="commands">Commands ({template.commands.length})</TabsTrigger>
          <TabsTrigger value="slots">Slots ({template.slots.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Template</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <div className="text-xs text-muted-foreground">Name</div>
                  <div className="text-sm">{template.name}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Slug</div>
                  <div className="text-sm font-mono">{template.slug}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Category</div>
                  <div className="text-sm">{categoryLabels[template.category] ?? template.category}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Source</div>
                  <div className="text-sm">{template.source}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Manufacturer</div>
                  <div className="text-sm">{template.manufacturer ?? "—"}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Model</div>
                  <div className="text-sm">{template.model ?? "—"}</div>
                </div>
                <div className="md:col-span-2">
                  <div className="text-xs text-muted-foreground">Description</div>
                  <div className="text-sm">{template.description ?? "—"}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Firmware Version Pattern</div>
                  <div className="text-sm font-mono break-all">{template.firmware_version_pattern ?? "—"}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Image URL</div>
                  <div className="text-sm break-all">{template.image_url ?? "—"}</div>
                </div>
                <div className="md:col-span-2">
                  <div className="text-xs text-muted-foreground">Transport Defaults</div>
                  <pre className="mt-1 rounded-md border border-border bg-muted/30 p-2 text-xs overflow-auto">
                    {safeJsonStringify(template.transport_defaults ?? {})}
                  </pre>
                </div>
                <div className="md:col-span-2">
                  <div className="text-xs text-muted-foreground">Metadata</div>
                  <pre className="mt-1 rounded-md border border-border bg-muted/30 p-2 text-xs overflow-auto">
                    {safeJsonStringify(template.metadata ?? {})}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics">
          <div className="space-y-3">
            {editable ? (
              <div className="flex justify-end">
                <Button onClick={openAddMetric}>
                  <Plus className="mr-1 h-4 w-4" />
                  Add Metric
                </Button>
              </div>
            ) : null}
            <DataTable
              columns={metricsColumns}
              data={template.metrics}
              emptyState={
                <EmptyState
                  title="No metrics"
                  description={editable ? "Add the first metric for this template." : "This template has no metrics."}
                />
              }
            />
          </div>
        </TabsContent>

        <TabsContent value="commands">
          <div className="space-y-3">
            {editable ? (
              <div className="flex justify-end">
                <Button onClick={openAddCommand}>
                  <Plus className="mr-1 h-4 w-4" />
                  Add Command
                </Button>
              </div>
            ) : null}
            <DataTable
              columns={commandsColumns}
              data={template.commands}
              emptyState={
                <EmptyState
                  title="No commands"
                  description={editable ? "Add the first command for this template." : "This template has no commands."}
                />
              }
            />
          </div>
        </TabsContent>

        <TabsContent value="slots">
          <div className="space-y-3">
            {editable ? (
              <div className="flex justify-end">
                <Button onClick={openAddSlot}>
                  <Plus className="mr-1 h-4 w-4" />
                  Add Slot
                </Button>
              </div>
            ) : null}
            <DataTable
              columns={slotsColumns}
              data={template.slots}
              emptyState={
                <EmptyState
                  title="No slots"
                  description={editable ? "Add the first slot for this template." : "This template has no slots."}
                />
              }
            />
          </div>
        </TabsContent>
      </Tabs>

      {/* Overview edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit Template</DialogTitle>
            <DialogDescription>Update template identity and config.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                value={editDraft.name ?? ""}
                onChange={(e) => setEditDraft((p) => ({ ...p, name: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Category</label>
              <Select
                value={String(editDraft.category ?? template.category)}
                onValueChange={(v) => setEditDraft((p) => ({ ...p, category: v }))}
              >
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
            <div className="grid gap-2">
              <label className="text-sm font-medium">Manufacturer</label>
              <Input
                value={editDraft.manufacturer ?? ""}
                onChange={(e) => setEditDraft((p) => ({ ...p, manufacturer: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Model</label>
              <Input
                value={editDraft.model ?? ""}
                onChange={(e) => setEditDraft((p) => ({ ...p, model: e.target.value }))}
              />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                value={editDraft.description ?? ""}
                onChange={(e) => setEditDraft((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Firmware Version Pattern</label>
              <Input
                value={editDraft.firmware_version_pattern ?? ""}
                onChange={(e) =>
                  setEditDraft((p) => ({ ...p, firmware_version_pattern: e.target.value }))
                }
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Image URL</label>
              <Input
                value={editDraft.image_url ?? ""}
                onChange={(e) => setEditDraft((p) => ({ ...p, image_url: e.target.value }))}
              />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Transport Defaults (JSON)</label>
              <Textarea value={editTransportDefaults} onChange={(e) => setEditTransportDefaults(e.target.value)} />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Metadata (JSON)</label>
              <Textarea value={editMetadata} onChange={(e) => setEditMetadata(e.target.value)} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)} disabled={updateTemplateMutation.isPending}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                try {
                  const transport_defaults = parseJsonObject(editTransportDefaults) ?? {};
                  const metadata = parseJsonObject(editMetadata) ?? {};
                  updateTemplateMutation.mutate({
                    templateIdToUpdate: id,
                    data: {
                      ...editDraft,
                      transport_defaults,
                      metadata,
                    },
                  });
                } catch (e) {
                  toast.error(getErrorMessage(e) || "Invalid JSON");
                }
              }}
              disabled={updateTemplateMutation.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Metric dialog */}
      <Dialog open={metricOpen} onOpenChange={setMetricOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editingMetric ? "Edit Metric" : "Add Metric"}</DialogTitle>
            <DialogDescription>Define a metric supported by this template.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Metric Key</label>
              <Input
                value={metricDraft.metric_key}
                onChange={(e) => setMetricDraft((p) => ({ ...p, metric_key: e.target.value }))}
                disabled={!!editingMetric}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Display Name</label>
              <Input
                value={metricDraft.display_name}
                onChange={(e) => setMetricDraft((p) => ({ ...p, display_name: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Data Type</label>
              <Select
                value={String(metricDraft.data_type)}
                onValueChange={(v) => setMetricDraft((p) => ({ ...p, data_type: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="float">float</SelectItem>
                  <SelectItem value="integer">integer</SelectItem>
                  <SelectItem value="boolean">boolean</SelectItem>
                  <SelectItem value="string">string</SelectItem>
                  <SelectItem value="enum">enum</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Unit</label>
              <Input value={metricDraft.unit ?? ""} onChange={(e) => setMetricDraft((p) => ({ ...p, unit: e.target.value }))} />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Min</label>
              <Input
                type="number"
                value={metricDraft.min_value ?? ""}
                onChange={(e) =>
                  setMetricDraft((p) => ({
                    ...p,
                    min_value: e.target.value === "" ? undefined : Number(e.target.value),
                  }))
                }
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Max</label>
              <Input
                type="number"
                value={metricDraft.max_value ?? ""}
                onChange={(e) =>
                  setMetricDraft((p) => ({
                    ...p,
                    max_value: e.target.value === "" ? undefined : Number(e.target.value),
                  }))
                }
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Precision Digits</label>
              <Input
                type="number"
                value={metricDraft.precision_digits ?? 2}
                onChange={(e) =>
                  setMetricDraft((p) => ({ ...p, precision_digits: Number(e.target.value) }))
                }
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Required</label>
              <Select
                value={metricDraft.is_required ? "yes" : "no"}
                onValueChange={(v) => setMetricDraft((p) => ({ ...p, is_required: v === "yes" }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="no">No</SelectItem>
                  <SelectItem value="yes">Yes</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                value={metricDraft.description ?? ""}
                onChange={(e) => setMetricDraft((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
            {metricDraft.data_type === "enum" ? (
              <div className="grid gap-2 md:col-span-2">
                <label className="text-sm font-medium">Enum Values (comma-separated)</label>
                <Input
                  value={(metricDraft.enum_values ?? []).join(", ")}
                  onChange={(e) =>
                    setMetricDraft((p) => ({
                      ...p,
                      enum_values: e.target.value
                        .split(",")
                        .map((v) => v.trim())
                        .filter(Boolean),
                    }))
                  }
                />
              </div>
            ) : null}
            <div className="grid gap-2">
              <label className="text-sm font-medium">Sort Order</label>
              <Input
                type="number"
                value={metricDraft.sort_order ?? 0}
                onChange={(e) => setMetricDraft((p) => ({ ...p, sort_order: Number(e.target.value) }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMetricOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                const payload: TemplateMetricPayload = {
                  ...metricDraft,
                  unit: metricDraft.unit?.trim() ? metricDraft.unit.trim() : undefined,
                  description: metricDraft.description?.trim() ? metricDraft.description.trim() : undefined,
                  enum_values:
                    metricDraft.data_type === "enum" ? metricDraft.enum_values ?? [] : undefined,
                };
                if (editingMetric) {
                  updateMetricMutation.mutate({
                    templateIdForMetric: id,
                    metricId: editingMetric.id,
                    data: payload,
                  });
                } else {
                  createMetricMutation.mutate({ templateIdForMetric: id, data: payload });
                }
              }}
              disabled={createMetricMutation.isPending || updateMetricMutation.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Command dialog */}
      <Dialog open={commandOpen} onOpenChange={setCommandOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editingCommand ? "Edit Command" : "Add Command"}</DialogTitle>
            <DialogDescription>Define a command supported by this template.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Command Key</label>
              <Input
                value={commandDraft.command_key}
                onChange={(e) => setCommandDraft((p) => ({ ...p, command_key: e.target.value }))}
                disabled={!!editingCommand}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Display Name</label>
              <Input
                value={commandDraft.display_name}
                onChange={(e) => setCommandDraft((p) => ({ ...p, display_name: e.target.value }))}
              />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                value={commandDraft.description ?? ""}
                onChange={(e) => setCommandDraft((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Parameters Schema (JSON)</label>
              <Textarea value={commandParametersJson} onChange={(e) => setCommandParametersJson(e.target.value)} />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Response Schema (JSON)</label>
              <Textarea value={commandResponseJson} onChange={(e) => setCommandResponseJson(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Sort Order</label>
              <Input
                type="number"
                value={commandDraft.sort_order ?? 0}
                onChange={(e) => setCommandDraft((p) => ({ ...p, sort_order: Number(e.target.value) }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCommandOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                try {
                  const parameters_schema = (parseJsonObject(commandParametersJson) ?? {}) as Record<string, unknown>;
                  const response_schema = (parseJsonObject(commandResponseJson) ?? {}) as Record<string, unknown>;
                  const payload: TemplateCommandPayload = {
                    ...commandDraft,
                    description: commandDraft.description?.trim() ? commandDraft.description.trim() : undefined,
                    parameters_schema,
                    response_schema,
                  };
                  if (editingCommand) {
                    updateCommandMutation.mutate({
                      templateIdForCommand: id,
                      commandId: editingCommand.id,
                      data: payload,
                    });
                  } else {
                    createCommandMutation.mutate({ templateIdForCommand: id, data: payload });
                  }
                } catch (e) {
                  toast.error(getErrorMessage(e) || "Invalid JSON");
                }
              }}
              disabled={createCommandMutation.isPending || updateCommandMutation.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Slot dialog */}
      <Dialog open={slotOpen} onOpenChange={setSlotOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editingSlot ? "Edit Slot" : "Add Slot"}</DialogTitle>
            <DialogDescription>Define expansion interfaces for this template.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Slot Key</label>
              <Input
                value={slotDraft.slot_key}
                onChange={(e) => setSlotDraft((p) => ({ ...p, slot_key: e.target.value }))}
                disabled={!!editingSlot}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Display Name</label>
              <Input
                value={slotDraft.display_name}
                onChange={(e) => setSlotDraft((p) => ({ ...p, display_name: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Slot Type</label>
              <Select value={String(slotDraft.slot_type)} onValueChange={(v) => setSlotDraft((p) => ({ ...p, slot_type: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="expansion">expansion</SelectItem>
                  <SelectItem value="sensor">sensor</SelectItem>
                  <SelectItem value="accessory">accessory</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Interface Type</label>
              <Input
                value={slotDraft.interface_type}
                onChange={(e) => setSlotDraft((p) => ({ ...p, interface_type: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Max Devices</label>
              <Input
                type="number"
                value={slotDraft.max_devices ?? ""}
                onChange={(e) =>
                  setSlotDraft((p) => ({
                    ...p,
                    max_devices: e.target.value === "" ? undefined : Number(e.target.value),
                  }))
                }
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Required</label>
              <Select
                value={slotDraft.is_required ? "yes" : "no"}
                onValueChange={(v) => setSlotDraft((p) => ({ ...p, is_required: v === "yes" }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="no">No</SelectItem>
                  <SelectItem value="yes">Yes</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Compatible Templates</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="justify-between">
                    {slotDraft.compatible_templates && slotDraft.compatible_templates.length
                      ? `${slotDraft.compatible_templates.length} selected`
                      : "Select expansion modules"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[320px]" align="start">
                  {expansionModules.length ? (
                    expansionModules.map((t) => {
                      const selected = (slotDraft.compatible_templates ?? []).includes(t.id);
                      return (
                        <DropdownMenuCheckboxItem
                          key={t.id}
                          checked={selected}
                          onCheckedChange={(checked) => {
                            setSlotDraft((p) => {
                              const cur = new Set<number>(p.compatible_templates ?? []);
                              if (checked) cur.add(t.id);
                              else cur.delete(t.id);
                              return { ...p, compatible_templates: Array.from(cur).sort((a, b) => a - b) };
                            });
                          }}
                        >
                          {t.name}
                        </DropdownMenuCheckboxItem>
                      );
                    })
                  ) : (
                    <div className="px-2 py-1.5 text-sm text-muted-foreground">No expansion module templates</div>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div className="grid gap-2 md:col-span-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                value={slotDraft.description ?? ""}
                onChange={(e) => setSlotDraft((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Sort Order</label>
              <Input
                type="number"
                value={slotDraft.sort_order ?? 0}
                onChange={(e) => setSlotDraft((p) => ({ ...p, sort_order: Number(e.target.value) }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSlotOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                const payload: TemplateSlotPayload = {
                  ...slotDraft,
                  description: slotDraft.description?.trim() ? slotDraft.description.trim() : undefined,
                  compatible_templates: (slotDraft.compatible_templates ?? []).length
                    ? (slotDraft.compatible_templates ?? [])
                    : undefined,
                };
                if (editingSlot) {
                  updateSlotMutation.mutate({
                    templateIdForSlot: id,
                    slotId: editingSlot.id,
                    data: payload,
                  });
                } else {
                  createSlotMutation.mutate({ templateIdForSlot: id, data: payload });
                }
              }}
              disabled={createSlotMutation.isPending || updateSlotMutation.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirms */}
      <AlertDialog open={!!deletingMetric} onOpenChange={(open) => (!open ? setDeletingMetric(null) : null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete metric?</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingMetric ? (
                <>
                  This will remove <span className="font-medium">{deletingMetric.metric_key}</span>.
                </>
              ) : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingMetric(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (!deletingMetric) return;
                deleteMetricMutation.mutate({ templateIdForMetric: id, metricId: deletingMetric.id });
                setDeletingMetric(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!deletingCommand} onOpenChange={(open) => (!open ? setDeletingCommand(null) : null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete command?</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingCommand ? (
                <>
                  This will remove <span className="font-medium">{deletingCommand.command_key}</span>.
                </>
              ) : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingCommand(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (!deletingCommand) return;
                deleteCommandMutation.mutate({ templateIdForCommand: id, commandId: deletingCommand.id });
                setDeletingCommand(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!deletingSlot} onOpenChange={(open) => (!open ? setDeletingSlot(null) : null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete slot?</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingSlot ? (
                <>
                  This will remove <span className="font-medium">{deletingSlot.slot_key}</span>.
                </>
              ) : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingSlot(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (!deletingSlot) return;
                deleteSlotMutation.mutate({ templateIdForSlot: id, slotId: deletingSlot.id });
                setDeletingSlot(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}


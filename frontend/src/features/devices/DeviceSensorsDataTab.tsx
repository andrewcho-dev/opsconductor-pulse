import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import type { TelemetryPoint } from "@/services/api/types";
import {
  createDeviceModule,
  deleteDeviceModule,
  listDeviceModules,
} from "@/services/api/devices";
import type {
  DeviceModule,
  DeviceSensor,
  DeviceSensorCreate,
  DeviceSensorUpdate,
  ModuleCreatePayload,
} from "@/services/api/types";
import {
  createDeviceSensor,
  deleteDeviceSensor,
  listDeviceSensors,
  updateDeviceSensor,
} from "@/services/api/sensors";
import { getTemplate, listTemplates } from "@/services/api/templates";
import type { DeviceTemplate, TemplateDetail, TemplateSlot } from "@/services/api/templates";
import { getErrorMessage } from "@/lib/errors";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { TelemetryChartsSection } from "./TelemetryChartsSection";
import type { TimeRange } from "@/lib/charts";

function parseJsonObject(input: string): Record<string, string> {
  const trimmed = input.trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Metric key map must be a JSON object");
  }
  return parsed as Record<string, string>;
}

function sourceBadge(source: DeviceSensor["source"]) {
  const variant = source === "required" ? "default" : source === "optional" ? "secondary" : "outline";
  return <Badge variant={variant}>{source}</Badge>;
}

function statusBadge(status: DeviceSensor["status"]) {
  const variant = status === "active" ? "default" : status === "inactive" ? "secondary" : "destructive";
  return <Badge variant={variant}>{status}</Badge>;
}

function slotBadge(slot: TemplateSlot) {
  const v = slot.interface_type || slot.slot_type;
  return <Badge variant="outline">{v}</Badge>;
}

function AssignModuleDialog({
  deviceId,
  slot,
  moduleTemplates,
  onDone,
}: {
  deviceId: string;
  slot: TemplateSlot;
  moduleTemplates: DeviceTemplate[];
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [moduleTemplateId, setModuleTemplateId] = useState<string>("");
  const [label, setLabel] = useState("");
  const [busAddress, setBusAddress] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [metricKeyMapText, setMetricKeyMapText] = useState("{}");

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: ModuleCreatePayload = {
        slot_key: slot.slot_key,
        label: label.trim(),
        bus_address: busAddress.trim() || undefined,
        serial_number: serialNumber.trim() || undefined,
        module_template_id: moduleTemplateId ? Number(moduleTemplateId) : undefined,
        metric_key_map: parseJsonObject(metricKeyMapText),
      };
      if (!payload.label) throw new Error("Label is required");
      return createDeviceModule(deviceId, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-modules", deviceId] });
      toast.success("Module assigned");
      setOpen(false);
      onDone();
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to assign module"),
  });

  const compatible = useMemo(() => {
    if (!slot.compatible_templates || slot.compatible_templates.length === 0) return moduleTemplates;
    const allowed = new Set(slot.compatible_templates);
    return moduleTemplates.filter((t) => allowed.has(t.id));
  }, [moduleTemplates, slot.compatible_templates]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Assign Module</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Assign Module</DialogTitle>
          <DialogDescription>
            Assign an expansion module to slot <span className="font-mono">{slot.slot_key}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Module Template (optional)</div>
              <select
                className="h-10 w-full rounded border border-border bg-background px-2 text-sm"
                value={moduleTemplateId}
                onChange={(e) => setModuleTemplateId(e.target.value)}
              >
                <option value="">(custom / unknown)</option>
                {compatible.map((t) => (
                  <option key={t.id} value={String(t.id)}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Label</div>
              <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Port 1 Soil Probe" />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Bus Address (optional)</div>
              <Input value={busAddress} onChange={(e) => setBusAddress(e.target.value)} placeholder="e.g. 3" />
            </div>
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Serial Number (optional)</div>
              <Input
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                placeholder="e.g. SN1234"
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Metric Key Map (JSON)</div>
            <Textarea
              className="font-mono"
              rows={6}
              value={metricKeyMapText}
              onChange={(e) => setMetricKeyMapText(e.target.value)}
              placeholder='{"temperature":"port_1_temp"}'
            />
            <div className="text-xs text-muted-foreground">
              Map semantic metric keys to raw firmware keys (used by ingest normalization in later phases).
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Assigning..." : "Assign"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddSensorDialog({
  deviceId,
  template,
  onDone,
}: {
  deviceId: string;
  template: TemplateDetail | null | undefined;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"template" | "custom">("template");

  const [templateMetricId, setTemplateMetricId] = useState<string>("");
  const [metricKey, setMetricKey] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [unit, setUnit] = useState("");
  const [minRange, setMinRange] = useState("");
  const [maxRange, setMaxRange] = useState("");
  const [precisionDigits, setPrecisionDigits] = useState("2");

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: DeviceSensorCreate = {
        metric_key: metricKey.trim(),
        display_name: displayName.trim(),
        unit: unit.trim() || undefined,
        min_range: minRange ? Number(minRange) : undefined,
        max_range: maxRange ? Number(maxRange) : undefined,
        precision_digits: precisionDigits ? Number(precisionDigits) : undefined,
      };
      if (mode === "template" && templateMetricId) {
        payload.template_metric_id = Number(templateMetricId);
        const tm = template?.metrics?.find((m) => m.id === payload.template_metric_id);
        if (tm) {
          payload.metric_key = tm.metric_key;
          payload.display_name = tm.display_name;
          payload.unit = tm.unit ?? undefined;
          payload.precision_digits = tm.precision_digits;
        }
      }
      if (!payload.metric_key || !payload.display_name) {
        throw new Error("Metric key and display name are required");
      }
      return createDeviceSensor(deviceId, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-sensors", deviceId] });
      toast.success("Sensor added");
      setOpen(false);
      onDone();
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to add sensor"),
  });

  const templateMetrics = template?.metrics ?? [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Add Sensor</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Sensor</DialogTitle>
          <DialogDescription>Create an optional/custom sensor for this device.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="flex gap-2">
            <Button size="sm" variant={mode === "template" ? "default" : "outline"} onClick={() => setMode("template")}>
              From Template
            </Button>
            <Button size="sm" variant={mode === "custom" ? "default" : "outline"} onClick={() => setMode("custom")}>
              Custom
            </Button>
          </div>

          {mode === "template" ? (
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Template Metric</div>
              <select
                className="h-10 w-full rounded border border-border bg-background px-2 text-sm"
                value={templateMetricId}
                onChange={(e) => setTemplateMetricId(e.target.value)}
              >
                <option value="">Select a metric</option>
                {templateMetrics.map((m) => (
                  <option key={m.id} value={String(m.id)}>
                    {m.display_name} ({m.metric_key})
                  </option>
                ))}
              </select>
              {!template && <div className="text-xs text-muted-foreground">No template assigned to this device.</div>}
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Metric Key</div>
                <Input value={metricKey} onChange={(e) => setMetricKey(e.target.value)} placeholder="e.g. temperature" />
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Display Name</div>
                <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Temperature" />
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Unit</div>
                <Input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="C" />
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Precision Digits</div>
                <Input
                  type="number"
                  min={0}
                  max={6}
                  value={precisionDigits}
                  onChange={(e) => setPrecisionDigits(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Min Range</div>
                <Input value={minRange} onChange={(e) => setMinRange(e.target.value)} placeholder="(optional)" />
              </div>
              <div className="space-y-1">
                <div className="text-sm text-muted-foreground">Max Range</div>
                <Input value={maxRange} onChange={(e) => setMaxRange(e.target.value)} placeholder="(optional)" />
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Adding..." : "Add"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditSensorDialog({
  deviceId,
  sensor,
  onDone,
}: {
  deviceId: string;
  sensor: DeviceSensor;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [displayName, setDisplayName] = useState(sensor.display_name ?? "");
  const [unit, setUnit] = useState(sensor.unit ?? "");
  const [minRange, setMinRange] = useState(sensor.min_range != null ? String(sensor.min_range) : "");
  const [maxRange, setMaxRange] = useState(sensor.max_range != null ? String(sensor.max_range) : "");
  const [precisionDigits, setPrecisionDigits] = useState(String(sensor.precision_digits ?? 2));
  const [status, setStatus] = useState<string>(sensor.status);

  const updateMutation = useMutation({
    mutationFn: async () => {
      const payload: DeviceSensorUpdate = {
        display_name: displayName.trim() || undefined,
        unit: unit.trim() || undefined,
        min_range: minRange ? Number(minRange) : undefined,
        max_range: maxRange ? Number(maxRange) : undefined,
        precision_digits: precisionDigits ? Number(precisionDigits) : undefined,
        status,
      };
      return updateDeviceSensor(deviceId, sensor.id, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-sensors", deviceId] });
      toast.success("Sensor updated");
      setOpen(false);
      onDone();
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to update sensor"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit Sensor</DialogTitle>
          <DialogDescription className="font-mono">{sensor.metric_key}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Display Name</div>
            <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Unit</div>
            <Input value={unit} onChange={(e) => setUnit(e.target.value)} />
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Min Range</div>
            <Input value={minRange} onChange={(e) => setMinRange(e.target.value)} />
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Max Range</div>
            <Input value={maxRange} onChange={(e) => setMaxRange(e.target.value)} />
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Precision Digits</div>
            <Input
              type="number"
              min={0}
              max={6}
              value={precisionDigits}
              onChange={(e) => setPrecisionDigits(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Status</div>
            <select
              className="h-10 w-full rounded border border-border bg-background px-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="active">active</option>
              <option value="inactive">inactive</option>
              <option value="error">error</option>
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DeviceSensorsDataTab({
  deviceId,
  templateId,
  telemetry,
}: {
  deviceId: string;
  templateId?: number | null;
  telemetry: {
    points: TelemetryPoint[];
    metrics: string[];
    isLoading: boolean;
    isLive: boolean;
    liveCount: number;
    timeRange: TimeRange;
    onTimeRangeChange: (range: TimeRange) => void;
  };
}) {
  const queryClient = useQueryClient();

  const sensorsQuery = useQuery({
    queryKey: ["device-sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId),
    enabled: !!deviceId,
  });

  const modulesQuery = useQuery({
    queryKey: ["device-modules", deviceId],
    queryFn: () => listDeviceModules(deviceId),
    enabled: !!deviceId,
  });

  const templateQuery = useQuery({
    queryKey: ["templates", templateId],
    queryFn: () => getTemplate(templateId!),
    enabled: !!templateId,
  });

  const moduleTemplatesQuery = useQuery({
    queryKey: ["templates", "expansion_module"],
    queryFn: () => listTemplates({ category: "expansion_module" }),
  });

  const sensors = sensorsQuery.data?.sensors ?? [];
  const modules = modulesQuery.data ?? [];
  const template = templateQuery.data;
  const slots = (template?.slots ?? []).slice().sort((a, b) => a.sort_order - b.sort_order);
  const moduleTemplates = moduleTemplatesQuery.data ?? [];

  const activeMetricKeys = useMemo(() => {
    return sensors.filter((s) => s.status === "active").map((s) => s.metric_key);
  }, [sensors]);

  const deleteSensorMutation = useMutation({
    mutationFn: async (sensorId: number) => deleteDeviceSensor(deviceId, sensorId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-sensors", deviceId] });
      toast.success("Sensor deleted");
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to delete sensor"),
  });

  const deleteModuleMutation = useMutation({
    mutationFn: async (moduleId: number) => deleteDeviceModule(deviceId, moduleId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-modules", deviceId] });
      toast.success("Module removed");
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to remove module"),
  });

  const moduleColumns: ColumnDef<DeviceModule>[] = useMemo(
    () => [
      { accessorKey: "slot_key", header: "Slot" },
      { accessorKey: "label", header: "Label" },
      {
        id: "template",
        header: "Template",
        cell: ({ row }) => row.original.module_template?.name ?? "—",
      },
      {
        id: "status",
        header: "Status",
        cell: ({ row }) => <Badge variant="outline">{row.original.status}</Badge>,
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="outline">
                Remove
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Remove module?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will mark the module as removed and deactivate linked sensors.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => deleteModuleMutation.mutate(row.original.id)}
                  disabled={deleteModuleMutation.isPending}
                >
                  {deleteModuleMutation.isPending ? "Removing..." : "Remove"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ),
      },
    ],
    [deleteModuleMutation]
  );

  const sensorColumns: ColumnDef<DeviceSensor>[] = useMemo(
    () => [
      { accessorKey: "metric_key", header: "Metric Key" },
      { accessorKey: "display_name", header: "Display Name" },
      {
        id: "source",
        header: "Source",
        cell: ({ row }) => sourceBadge(row.original.source),
      },
      {
        id: "module",
        header: "Module",
        cell: ({ row }) => row.original.module?.label ?? "Built-in",
      },
      { accessorKey: "unit", header: "Unit", cell: ({ row }) => row.original.unit ?? "—" },
      {
        id: "last_value",
        header: "Last Value",
        cell: ({ row }) => row.original.last_value_text ?? (row.original.last_value != null ? String(row.original.last_value) : "—"),
      },
      {
        accessorKey: "last_seen_at",
        header: "Last Seen",
        cell: ({ row }) =>
          row.original.last_seen_at ? (
            <span className="text-xs text-muted-foreground">
              {new Date(row.original.last_seen_at).toLocaleString()}
            </span>
          ) : (
            "—"
          ),
      },
      {
        id: "status",
        header: "Status",
        cell: ({ row }) => statusBadge(row.original.status),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <EditSensorDialog deviceId={deviceId} sensor={row.original} onDone={() => {}} />
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="outline" disabled={row.original.source === "required"}>
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete sensor?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Required sensors cannot be deleted. You can deactivate optional/custom sensors instead.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => deleteSensorMutation.mutate(row.original.id)}
                    disabled={deleteSensorMutation.isPending || row.original.source === "required"}
                  >
                    {deleteSensorMutation.isPending ? "Deleting..." : "Delete"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        ),
      },
    ],
    [deleteSensorMutation, deviceId]
  );

  return (
    <div className="space-y-6 pt-2">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">Expansion Modules</div>
            <div className="text-sm text-muted-foreground">
              Assign expansion modules to template slots (if available).
            </div>
          </div>
        </div>

        {!templateId ? (
          <div className="rounded border border-border p-4 text-sm text-muted-foreground">
            No template assigned to this device. Assign a template to enable slot/module management.
          </div>
        ) : slots.length === 0 ? (
          <div className="rounded border border-border p-4 text-sm text-muted-foreground">
            This template has no slots defined.
          </div>
        ) : (
          <div className="grid gap-3">
            {slots.map((slot) => {
              const assigned = modules.filter((m) => m.slot_key === slot.slot_key && m.status !== "removed");
              const max = slot.max_devices ?? null;
              const capacityText = max != null ? `${assigned.length}/${max} assigned` : `${assigned.length} assigned`;
              const canAssign = max == null || assigned.length < max;
              return (
                <div key={slot.id} className="rounded border border-border p-4 space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm">{slot.slot_key}</span>
                        <span className="text-sm font-medium">{slot.display_name}</span>
                        {slotBadge(slot)}
                        {slot.is_required && <Badge>required</Badge>}
                      </div>
                      <div className="text-sm text-muted-foreground">{capacityText}</div>
                    </div>
                    {canAssign ? (
                      <AssignModuleDialog
                        deviceId={deviceId}
                        slot={slot}
                        moduleTemplates={moduleTemplates}
                        onDone={() => {}}
                      />
                    ) : (
                      <Button size="sm" variant="outline" disabled>
                        At capacity
                      </Button>
                    )}
                  </div>

                  {assigned.length === 0 ? (
                    <div className="text-sm text-muted-foreground">No modules assigned.</div>
                  ) : (
                    <DataTable
                      columns={moduleColumns}
                      data={assigned}
                      isLoading={modulesQuery.isLoading}
                      manualPagination={false}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">Sensors</div>
            <div className="text-sm text-muted-foreground">Manage device sensors and their metadata.</div>
          </div>
          <AddSensorDialog deviceId={deviceId} template={template} onDone={() => {}} />
        </div>

        <DataTable
          columns={sensorColumns}
          data={sensors}
          isLoading={sensorsQuery.isLoading}
          emptyState={
            <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
              No sensors configured for this device yet.
            </div>
          }
          manualPagination={false}
        />
      </section>

      <section className="space-y-3">
        <div>
          <div className="text-sm font-semibold">Telemetry Charts</div>
          <div className="text-sm text-muted-foreground">Charts render for active sensors.</div>
        </div>
        <WidgetErrorBoundary widgetName="Telemetry Charts">
          <div className="h-[calc(100vh-420px)]">
            <TelemetryChartsSection
              deviceId={deviceId}
              metrics={activeMetricKeys.length > 0 ? activeMetricKeys : telemetry.metrics}
              points={telemetry.points}
              isLoading={telemetry.isLoading}
              isLive={telemetry.isLive}
              liveCount={telemetry.liveCount}
              timeRange={telemetry.timeRange}
              onTimeRangeChange={telemetry.onTimeRangeChange}
            />
          </div>
        </WidgetErrorBoundary>
      </section>
    </div>
  );
}


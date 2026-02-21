import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

import { getErrorMessage } from "@/lib/errors";
import {
  createSensor,
  deleteSensor,
  listDeviceSensors,
  updateSensor,
} from "@/services/api/sensors";
import type { Sensor, SensorCreate, SensorUpdate } from "@/services/api/types";

interface DeviceSensorsPanelProps {
  deviceId: string;
}

const SENSOR_TYPE_OPTIONS = [
  "temperature",
  "humidity",
  "pressure",
  "vibration",
  "flow",
  "level",
  "power",
  "electrical",
  "speed",
  "weight",
  "air_quality",
  "digital",
  "analog",
  "other",
] as const;

function parseOptionalNumber(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : undefined;
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "active":
      return "bg-status-online/10 text-status-online";
    case "disabled":
      return "bg-muted text-muted-foreground";
    case "stale":
      return "bg-status-warning/10 text-status-warning";
    case "error":
      return "bg-status-critical/10 text-status-critical";
    default:
      return "";
  }
}

export function DeviceSensorsPanel({ deviceId }: DeviceSensorsPanelProps) {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  // Legacy panel retained for backwards compatibility; the device detail page uses Phase 171 tabs.
  // `device_sensors` response shape differs from the original `sensors` shape, so we keep this loose.
  const [editSensorTarget, setEditSensorTarget] = useState<any | null>(null);
  const [deleteSensorTarget, setDeleteSensorTarget] = useState<any | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["device-sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId),
    enabled: !!deviceId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: SensorCreate) => createSensor(deviceId, payload),
    onSuccess: async () => {
      toast.success("Sensor created");
      setAddOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["device-sensors", deviceId] });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err) || "Failed to create sensor");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ sensorId, payload }: { sensorId: number; payload: SensorUpdate }) =>
      updateSensor(sensorId, payload),
    onSuccess: async () => {
      toast.success("Sensor updated");
      setEditSensorTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["device-sensors", deviceId] });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err) || "Failed to update sensor");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (sensorId: number) => deleteSensor(sensorId),
    onSuccess: async () => {
      toast.success("Sensor deleted");
      setDeleteSensorTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["device-sensors", deviceId] });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err) || "Failed to delete sensor");
    },
  });

  const columns: ColumnDef<any>[] = useMemo(
    () => [
      {
        accessorKey: "metric_name",
        header: "Metric",
        cell: ({ row }) => (
          <div>
            <div className="font-medium text-sm">{row.original.metric_name}</div>
            {row.original.label && (
              <div className="text-xs text-muted-foreground">{row.original.label}</div>
            )}
          </div>
        ),
      },
      {
        accessorKey: "sensor_type",
        header: "Type",
        cell: ({ row }) => (
          <Badge variant="secondary" className="text-xs">
            {row.original.sensor_type}
          </Badge>
        ),
      },
      {
        accessorKey: "last_value",
        header: "Last Value",
        cell: ({ row }) => {
          const s = row.original;
          if (s.last_value == null) return <span className="text-muted-foreground">—</span>;
          return (
            <span className="font-mono text-sm">
              {s.last_value.toFixed(s.precision_digits)} {s.unit ?? ""}
            </span>
          );
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge className={statusBadgeClass(row.original.status)}>{row.original.status}</Badge>
        ),
      },
      {
        accessorKey: "last_seen_at",
        header: "Last Seen",
        cell: ({ row }) => {
          if (!row.original.last_seen_at) {
            return <span className="text-muted-foreground">Never</span>;
          }
          return <span className="text-xs">{new Date(row.original.last_seen_at).toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "auto_discovered",
        header: "Source",
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground">
            {row.original.auto_discovered ? "Auto" : "Manual"}
          </span>
        ),
      },
      {
        id: "actions",
        cell: ({ row }) => (
          <div className="flex gap-1">
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              aria-label="Edit sensor"
              onClick={() => setEditSensorTarget(row.original)}
            >
              <Pencil className="h-3 w-3" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7 text-destructive"
              aria-label="Delete sensor"
              onClick={() => setDeleteSensorTarget(row.original)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Sensors</h3>
          <p className="text-xs text-muted-foreground">
            {data?.total ?? 0} / {data?.sensor_limit ?? "—"} sensors
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setAddOpen(true)}>
          <Plus className="mr-1 h-3 w-3" /> Add Sensor
        </Button>
      </div>

      <DataTable columns={columns} data={data?.sensors ?? []} isLoading={isLoading} />

      <AddSensorDialog
        open={addOpen}
        setOpen={setAddOpen}
        onSubmit={(payload) => createMutation.mutate(payload)}
        isSubmitting={createMutation.isPending}
      />

      <EditSensorDialog
        sensor={editSensorTarget}
        setSensor={setEditSensorTarget}
        onSubmit={(sensorId, payload) => updateMutation.mutate({ sensorId, payload })}
        isSubmitting={updateMutation.isPending}
      />

      <AlertDialog open={!!deleteSensorTarget} onOpenChange={(open) => !open && setDeleteSensorTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Sensor</AlertDialogTitle>
            <AlertDialogDescription>
              Delete sensor '{deleteSensorTarget?.metric_name}' from this device? Historical telemetry data
              will not be affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending || !deleteSensorTarget}
              onClick={() => deleteSensorTarget && deleteMutation.mutate(deleteSensorTarget.sensor_id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function AddSensorDialog({
  open,
  setOpen,
  onSubmit,
  isSubmitting,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
  onSubmit: (payload: SensorCreate) => void;
  isSubmitting: boolean;
}) {
  const [metricName, setMetricName] = useState("");
  const [sensorType, setSensorType] = useState<(typeof SENSOR_TYPE_OPTIONS)[number]>("temperature");
  const [label, setLabel] = useState("");
  const [unit, setUnit] = useState("");
  const [minRange, setMinRange] = useState("");
  const [maxRange, setMaxRange] = useState("");
  const [precisionDigits, setPrecisionDigits] = useState("1");

  useEffect(() => {
    if (!open) return;
    setMetricName("");
    setSensorType("temperature");
    setLabel("");
    setUnit("");
    setMinRange("");
    setMaxRange("");
    setPrecisionDigits("1");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Sensor</DialogTitle>
          <DialogDescription>Manually declare a sensor metric for this device.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="metric_name">Metric name</Label>
            <Input
              id="metric_name"
              value={metricName}
              onChange={(e) => setMetricName(e.target.value)}
              placeholder="e.g. ambient_temp"
            />
          </div>

          <div className="space-y-1">
            <Label>Sensor type</Label>
            <Select value={sensorType} onValueChange={(v) => setSensorType(v as any)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SENSOR_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt} value={opt}>
                    {opt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="label">Label (optional)</Label>
              <Input id="label" value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="unit">Unit (optional)</Label>
              <Input id="unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="min_range">Min range (optional)</Label>
              <Input
                id="min_range"
                type="number"
                value={minRange}
                onChange={(e) => setMinRange(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="max_range">Max range (optional)</Label>
              <Input
                id="max_range"
                type="number"
                value={maxRange}
                onChange={(e) => setMaxRange(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="precision_digits">Precision digits (0-6)</Label>
            <Input
              id="precision_digits"
              type="number"
              min={0}
              max={6}
              value={precisionDigits}
              onChange={(e) => setPrecisionDigits(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              const name = metricName.trim();
              const ok = /^[a-zA-Z][a-zA-Z0-9_]*$/.test(name);
              if (!ok) {
                toast.error("Metric name must match: ^[a-zA-Z][a-zA-Z0-9_]*$");
                return;
              }
              const payload: SensorCreate = {
                metric_name: name,
                sensor_type: sensorType,
                ...(label.trim() ? { label: label.trim() } : {}),
                ...(unit.trim() ? { unit: unit.trim() } : {}),
                ...(parseOptionalNumber(minRange) != null ? { min_range: parseOptionalNumber(minRange) } : {}),
                ...(parseOptionalNumber(maxRange) != null ? { max_range: parseOptionalNumber(maxRange) } : {}),
                ...(parseOptionalNumber(precisionDigits) != null
                  ? { precision_digits: Math.max(0, Math.min(6, Number(precisionDigits))) }
                  : {}),
              };
              onSubmit(payload);
            }}
            disabled={isSubmitting}
          >
            Add
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditSensorDialog({
  sensor,
  setSensor,
  onSubmit,
  isSubmitting,
}: {
  sensor: Sensor | null;
  setSensor: (next: Sensor | null) => void;
  onSubmit: (sensorId: number, payload: SensorUpdate) => void;
  isSubmitting: boolean;
}) {
  const open = !!sensor;
  const [sensorType, setSensorType] = useState<string>("temperature");
  const [label, setLabel] = useState("");
  const [unit, setUnit] = useState("");
  const [minRange, setMinRange] = useState("");
  const [maxRange, setMaxRange] = useState("");
  const [precisionDigits, setPrecisionDigits] = useState("1");
  const [status, setStatus] = useState<"active" | "disabled">("active");

  useEffect(() => {
    if (!sensor) return;
    setSensorType(sensor.sensor_type);
    setLabel(sensor.label ?? "");
    setUnit(sensor.unit ?? "");
    setMinRange(sensor.min_range != null ? String(sensor.min_range) : "");
    setMaxRange(sensor.max_range != null ? String(sensor.max_range) : "");
    setPrecisionDigits(String(sensor.precision_digits ?? 1));
    setStatus(sensor.status === "disabled" ? "disabled" : "active");
  }, [sensor]);

  return (
    <Dialog open={open} onOpenChange={(next) => !next && setSensor(null)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Sensor</DialogTitle>
          <DialogDescription>Update sensor metadata. Metric name is immutable.</DialogDescription>
        </DialogHeader>

        {sensor && (
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>Metric name</Label>
              <div className="text-sm font-mono">{sensor.metric_name}</div>
            </div>

            <div className="space-y-1">
              <Label>Sensor type</Label>
              <Select value={sensorType} onValueChange={setSensorType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SENSOR_TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt} value={opt}>
                      {opt}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="edit_label">Label</Label>
                <Input id="edit_label" value={label} onChange={(e) => setLabel(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="edit_unit">Unit</Label>
                <Input id="edit_unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="edit_min_range">Min range</Label>
                <Input
                  id="edit_min_range"
                  type="number"
                  value={minRange}
                  onChange={(e) => setMinRange(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="edit_max_range">Max range</Label>
                <Input
                  id="edit_max_range"
                  type="number"
                  value={maxRange}
                  onChange={(e) => setMaxRange(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="edit_precision">Precision digits</Label>
                <Input
                  id="edit_precision"
                  type="number"
                  min={0}
                  max={6}
                  value={precisionDigits}
                  onChange={(e) => setPrecisionDigits(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label>Status</Label>
                <Select value={status} onValueChange={(v) => setStatus(v as "active" | "disabled")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">active</SelectItem>
                    <SelectItem value="disabled">disabled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setSensor(null)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (!sensor) return;
              const payload: SensorUpdate = {
                sensor_type: sensorType,
                label: label.trim() ? label.trim() : undefined,
                unit: unit.trim() ? unit.trim() : undefined,
                min_range: parseOptionalNumber(minRange),
                max_range: parseOptionalNumber(maxRange),
                precision_digits:
                  parseOptionalNumber(precisionDigits) != null
                    ? Math.max(0, Math.min(6, Number(precisionDigits)))
                    : undefined,
                status,
              };
              onSubmit(sensor.sensor_id, payload);
            }}
            disabled={isSubmitting || !sensor}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


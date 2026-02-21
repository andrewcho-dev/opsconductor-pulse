# Task 002 — DeviceSensorsPanel Component

## File

Create `frontend/src/features/devices/DeviceSensorsPanel.tsx`

Then add it to `DeviceDetailPage.tsx`.

## Component Design

A panel showing all sensors on a device with:
- Sensor count vs limit (e.g., "5 / 10 sensors")
- DataTable with sensor list
- "Add Sensor" button (manual creation)
- Inline edit for label/unit/range
- Delete with confirmation
- Status badge (active = green, disabled = gray, stale = orange, error = red)

## Implementation

```tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { listDeviceSensors, createSensor, updateSensor, deleteSensor } from "@/services/api/sensors";
import { getErrorMessage } from "@/lib/errors";
import type { Sensor, SensorCreate, SensorUpdate } from "@/services/api/types";

interface DeviceSensorsPanelProps {
  deviceId: string;
}

export function DeviceSensorsPanel({ deviceId }: DeviceSensorsPanelProps) {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [editSensor, setEditSensor] = useState<Sensor | null>(null);
  const [deleteSensorTarget, setDeleteSensorTarget] = useState<Sensor | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["device-sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId),
    enabled: !!deviceId,
  });

  // ... mutations for create, update, delete (see below)
  // ... column definitions (see below)
  // ... add/edit dialogs

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

      <DataTable
        columns={columns}
        data={data?.sensors ?? []}
        isLoading={isLoading}
      />

      {/* Add Sensor Dialog */}
      {/* Edit Sensor Dialog */}
      {/* Delete Confirmation AlertDialog */}
    </div>
  );
}
```

## Table Columns

```typescript
const columns: ColumnDef<Sensor>[] = [
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
    cell: ({ row }) => {
      const statusColors: Record<string, string> = {
        active: "bg-green-500/10 text-green-600",
        disabled: "bg-gray-500/10 text-gray-500",
        stale: "bg-orange-500/10 text-orange-600",
        error: "bg-red-500/10 text-red-600",
      };
      return (
        <Badge className={statusColors[row.original.status] ?? ""}>
          {row.original.status}
        </Badge>
      );
    },
  },
  {
    accessorKey: "last_seen_at",
    header: "Last Seen",
    cell: ({ row }) => {
      if (!row.original.last_seen_at) return <span className="text-muted-foreground">Never</span>;
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
        <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setEditSensor(row.original)}>
          <Pencil className="h-3 w-3" />
        </Button>
        <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => setDeleteSensorTarget(row.original)}>
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    ),
  },
];
```

## Add Sensor Dialog

Use a `Dialog` (not AlertDialog) with form fields:
- `metric_name` (Input, required) — only shown for manual add, pattern: `^[a-zA-Z][a-zA-Z0-9_]*$`
- `sensor_type` (Select) — temperature, humidity, pressure, vibration, flow, level, power, electrical, speed, weight, air_quality, digital, analog, other
- `label` (Input, optional)
- `unit` (Input, optional)
- `min_range` / `max_range` (Input number, optional) — side by side
- `precision_digits` (Input number, 0-6, default 1)

On submit: call `createSensor(deviceId, formData)`, invalidate query, toast success, close dialog.

## Edit Sensor Dialog

Same form as Add but pre-populated. `metric_name` is read-only (shown as text, not editable).
On submit: call `updateSensor(sensorId, formData)`, invalidate query, toast success, close dialog.

## Delete Confirmation

Use `AlertDialog`:
- Title: "Delete Sensor"
- Description: "Delete sensor '{metric_name}' from this device? Historical telemetry data will not be affected."
- Actions: Cancel / Delete

On confirm: call `deleteSensor(sensorId)`, invalidate query, toast success.

## Add to DeviceDetailPage.tsx

Import and add the panel to the vertical stack. Place it **after DeviceInfoCard/DeviceMapCard grid and before DeviceApiTokensPanel** — sensors are a core device feature and should be prominently positioned.

```tsx
import { DeviceSensorsPanel } from "./DeviceSensorsPanel";

// In the JSX, after the grid and tier card:
{deviceId && <DeviceSensorsPanel deviceId={deviceId} />}
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

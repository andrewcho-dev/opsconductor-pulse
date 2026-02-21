# Task 005 — Sensor List Page (Cross-Device View)

## File

Create `frontend/src/features/devices/SensorListPage.tsx`

## Purpose

A dedicated page at `/sensors` showing ALL sensors across ALL devices for the tenant. Users can filter by sensor type, status, and device. This enables viewing/organizing by sensor type — e.g., "show me all temperature sensors across the fleet."

## Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Sensors                                                      │
│  Manage and monitor all sensors across your device fleet      │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Type: [All ▼]  Status: [All ▼]  Device: [All ▼]  [Search]│ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Metric       │ Type    │ Device │ Value  │ Status│ Seen  │ │
│  │ temperature  │ temp    │ GW-001 │ 22.4°C │ ● act │ 1m    │ │
│  │ humidity     │ humid   │ GW-001 │ 45.2%  │ ● act │ 1m    │ │
│  │ temperature  │ temp    │ GW-002 │ 21.7°C │ ● act │ 2m    │ │
│  │ vibration_rms│ vib     │ GW-002 │ 2.34mm │ ● act │ 2m    │ │
│  │ ...          │         │        │        │       │       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  Showing 16 sensors across 4 devices                [< 1 >]  │
└───────────────────────────────────────────────────────────────┘
```

## Implementation

### Page Component

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { listAllSensors } from "@/services/api/sensors";
import { useDevices } from "@/hooks/use-devices";
import type { Sensor } from "@/services/api/types";

const SENSOR_TYPES = [
  "temperature", "humidity", "pressure", "vibration", "flow",
  "level", "power", "electrical", "speed", "weight",
  "air_quality", "battery", "digital", "analog", "unknown",
];

export function SensorListPage() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [deviceFilter, setDeviceFilter] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["all-sensors", typeFilter, statusFilter, deviceFilter],
    queryFn: () => listAllSensors({
      sensor_type: typeFilter || undefined,
      status: statusFilter || undefined,
      device_id: deviceFilter || undefined,
      limit: 200,
    }),
  });

  const { data: devicesData } = useDevices({ limit: 100 });
  // ... columns, filters, render
}
```

### Table Columns

```typescript
const columns: ColumnDef<Sensor>[] = [
  {
    accessorKey: "metric_name",
    header: "Metric",
    cell: ({ row }) => (
      <div>
        <div className="font-medium text-sm font-mono">{row.original.metric_name}</div>
        {row.original.label && (
          <div className="text-xs text-muted-foreground">{row.original.label}</div>
        )}
      </div>
    ),
  },
  {
    accessorKey: "sensor_type",
    header: "Type",
    cell: ({ row }) => <Badge variant="secondary">{row.original.sensor_type}</Badge>,
  },
  {
    accessorKey: "device_id",
    header: "Device",
    cell: ({ row }) => (
      <a href={`/devices/${row.original.device_id}`} className="text-sm text-primary underline underline-offset-2">
        {row.original.device_id}
      </a>
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
      const colors: Record<string, string> = {
        active: "bg-green-500/10 text-green-600",
        disabled: "bg-gray-500/10 text-gray-500",
        stale: "bg-orange-500/10 text-orange-600",
        error: "bg-red-500/10 text-red-600",
      };
      return <Badge className={colors[row.original.status] ?? ""}>{row.original.status}</Badge>;
    },
  },
  {
    accessorKey: "last_seen_at",
    header: "Last Seen",
    cell: ({ row }) => {
      if (!row.original.last_seen_at) return <span className="text-muted-foreground">Never</span>;
      // Show relative time (e.g., "2m ago", "1h ago")
      const diff = Date.now() - new Date(row.original.last_seen_at).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return <span className="text-xs text-green-600">Just now</span>;
      if (mins < 60) return <span className="text-xs">{mins}m ago</span>;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return <span className="text-xs">{hours}h ago</span>;
      return <span className="text-xs">{Math.floor(hours / 24)}d ago</span>;
    },
  },
];
```

### Filters

Three `Select` components in a row above the table:

```tsx
<div className="flex gap-3">
  <Select value={typeFilter} onValueChange={setTypeFilter}>
    <SelectTrigger className="w-[180px]">
      <SelectValue placeholder="All Types" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="">All Types</SelectItem>
      {SENSOR_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
    </SelectContent>
  </Select>

  <Select value={statusFilter} onValueChange={setStatusFilter}>
    <SelectTrigger className="w-[150px]">
      <SelectValue placeholder="All Status" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="">All Status</SelectItem>
      <SelectItem value="active">Active</SelectItem>
      <SelectItem value="disabled">Disabled</SelectItem>
      <SelectItem value="stale">Stale</SelectItem>
      <SelectItem value="error">Error</SelectItem>
    </SelectContent>
  </Select>

  <Select value={deviceFilter} onValueChange={setDeviceFilter}>
    <SelectTrigger className="w-[180px]">
      <SelectValue placeholder="All Devices" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="">All Devices</SelectItem>
      {devicesData?.devices?.map(d => (
        <SelectItem key={d.device_id} value={d.device_id}>{d.device_id}</SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

### Summary Footer

Below the table, show: "Showing {total} sensors across {uniqueDevices} devices"

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

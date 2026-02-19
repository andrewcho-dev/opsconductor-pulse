import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef } from "@tanstack/react-table";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/shared";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listAllSensors } from "@/services/api/sensors";
import { useDevices } from "@/hooks/use-devices";
import type { Sensor } from "@/services/api/types";

const SENSOR_TYPES = [
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
  "battery",
  "digital",
  "analog",
  "unknown",
] as const;

function statusBadgeClass(status: Sensor["status"]): string {
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

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  const diffMs = Date.now() - t;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function SensorListPage() {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [deviceFilter, setDeviceFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["all-sensors", typeFilter, statusFilter, deviceFilter],
    queryFn: () =>
      listAllSensors({
        sensor_type: typeFilter === "all" ? undefined : typeFilter,
        status: statusFilter === "all" ? undefined : statusFilter,
        device_id: deviceFilter === "all" ? undefined : deviceFilter,
        limit: 200,
      }),
  });

  const { data: devicesData } = useDevices({ limit: 100 });

  const sensors = data?.sensors ?? [];
  const uniqueDevices = useMemo(() => new Set(sensors.map((s) => s.device_id)).size, [sensors]);

  const columns: ColumnDef<Sensor>[] = useMemo(
    () => [
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
          <Link
            to={`/devices/${row.original.device_id}`}
            className="text-sm text-primary underline underline-offset-2"
          >
            {row.original.device_id}
          </Link>
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
          if (!row.original.last_seen_at) return <span className="text-muted-foreground">Never</span>;
          return <span className="text-xs">{relativeTime(row.original.last_seen_at)}</span>;
        },
      },
    ],
    [],
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Sensors"
        description="Manage and monitor all sensors across your device fleet"
      />

      <div className="rounded-md border border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/30 p-3 text-sm">
        <strong>Tip:</strong> You can now manage sensors per-device on the{" "}
        <strong>Sensors & Data</strong> tab of each device's detail page.
      </div>

      <div className="rounded-md border border-border p-3 space-y-3">
        <div className="flex gap-3 flex-wrap">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {SENSOR_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
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
              <SelectItem value="all">All Devices</SelectItem>
              {devicesData?.devices?.map((d) => (
                <SelectItem key={d.device_id} value={d.device_id}>
                  {d.device_id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DataTable columns={columns} data={sensors} isLoading={isLoading} />

        <div className="text-xs text-muted-foreground">
          Showing {data?.total ?? sensors.length} sensors across {uniqueDevices} devices
        </div>
      </div>
    </div>
  );
}


import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { memo } from "react";
import type { WidgetRendererProps } from "../widget-registry";

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function TableRendererInner({ config }: WidgetRendererProps) {
  const limit = asNumber(config.limit, 10);
  const filterStatus = asString(config.filter_status, "");

  const { data, isLoading } = useDevices({
    limit,
    offset: 0,
    status: filterStatus || undefined,
  });
  const devices = data?.devices || [];

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">No devices found.</p>
    );
  }

  return (
    <div className="rounded-md border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Device</TableHead>
            <TableHead>Site</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Battery</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {devices.map((d) => (
            <TableRow key={d.device_id}>
              <TableCell>
                <Link
                  to={`/devices/${d.device_id}`}
                  className="font-mono text-xs text-primary hover:underline"
                >
                  {d.device_id}
                </Link>
              </TableCell>
              <TableCell className="text-sm">{d.site_id}</TableCell>
              <TableCell>
                <StatusBadge status={d.status} />
              </TableCell>
              <TableCell className="text-right text-sm">
                {d.state?.battery_pct != null ? `${d.state.battery_pct}%` : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export default memo(TableRendererInner);


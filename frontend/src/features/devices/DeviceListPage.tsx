import { useState } from "react";
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
import { PageHeader, StatusBadge, EmptyState } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { Cpu } from "lucide-react";

export default function DeviceListPage() {
  const [offset, setOffset] = useState(0);
  const limit = 50;
  const { data, isLoading, error } = useDevices(limit, offset);

  const devices = data?.devices || [];
  const totalCount = data?.count || 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Devices"
        description={
          isLoading ? "Loading..." : `${totalCount} devices in your fleet`
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load devices: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : devices.length === 0 ? (
        <EmptyState
          title="No devices found"
          description="Devices will appear here once they connect and send data."
          icon={<Cpu className="h-12 w-12" />}
        />
      ) : (
        <>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device ID</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead className="text-right">Battery</TableHead>
                  <TableHead className="text-right">Metrics</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((d) => (
                  <TableRow key={d.device_id}>
                    <TableCell>
                      <Link
                        to={`/devices/${d.device_id}`}
                        className="font-mono text-sm text-primary hover:underline"
                      >
                        {d.device_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">{d.site_id}</TableCell>
                    <TableCell>
                      <StatusBadge status={d.status} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {d.last_seen_at || "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {d.state?.battery_pct != null
                        ? `${d.state.battery_pct}%`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground">
                      {d.state ? Object.keys(d.state).length : 0}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalCount > limit && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {offset + 1}–{Math.min(offset + limit, totalCount)} of{" "}
                {totalCount}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= totalCount}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

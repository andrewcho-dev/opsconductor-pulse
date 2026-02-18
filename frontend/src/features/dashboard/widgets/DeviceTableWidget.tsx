import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { memo } from "react";

function DeviceTableWidgetInner() {
  const { data, isLoading } = useDevices({ limit: 10, offset: 0 }); // Show top 10 on dashboard
  const devices = data?.devices || [];
  const totalCount = data?.total || 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Devices</CardTitle>
        {totalCount > 10 && (
          <Link to="/devices" className="text-xs text-primary hover:underline">
            View all {totalCount}
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : devices.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No devices found.
          </p>
        ) : (
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
                      {d.state?.battery_pct != null
                        ? `${d.state.battery_pct}%`
                        : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const DeviceTableWidget = memo(DeviceTableWidgetInner);

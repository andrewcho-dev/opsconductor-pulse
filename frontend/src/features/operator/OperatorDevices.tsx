import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, EmptyState, StatusBadge } from "@/components/shared";
import { useOperatorDevices } from "@/hooks/use-operator";
import { Server } from "lucide-react";

export default function OperatorDevices() {
  const [tenantFilterInput, setTenantFilterInput] = useState("");
  const [tenantFilter, setTenantFilter] = useState<string | undefined>(undefined);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const { data, isLoading, error } = useOperatorDevices(
    tenantFilter,
    limit,
    offset
  );

  const devices = data?.devices || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="All Devices"
        description="Cross-tenant device inventory"
      />

      <div className="flex flex-wrap gap-2">
        <Input
          value={tenantFilterInput}
          onChange={(e) => setTenantFilterInput(e.target.value)}
          placeholder="Filter by tenant_id"
          className="max-w-xs"
        />
        <Button
          variant="outline"
          onClick={() => {
            setTenantFilter(tenantFilterInput.trim() || undefined);
            setOffset(0);
          }}
        >
          Filter
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            setTenantFilterInput("");
            setTenantFilter(undefined);
            setOffset(0);
          }}
        >
          Clear
        </Button>
      </div>

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
          description="Try adjusting your tenant filter."
          icon={<Server className="h-12 w-12" />}
        />
      ) : (
        <>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant ID</TableHead>
                  <TableHead>Device ID</TableHead>
                  <TableHead>Site ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead className="text-right">Battery</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((d) => (
                  <TableRow key={`${d.tenant_id}-${d.device_id}`}>
                    <TableCell className="font-mono text-xs">
                      {d.tenant_id}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {d.device_id}
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Showing {offset + 1}–{offset + devices.length}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setOffset(offset + limit)}
                disabled={devices.length < limit}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

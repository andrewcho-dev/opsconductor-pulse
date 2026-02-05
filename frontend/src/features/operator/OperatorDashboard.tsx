import { useMemo } from "react";
import { PageHeader, SeverityBadge } from "@/components/shared";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
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
import { useOperatorAlerts, useOperatorDevices, useQuarantine } from "@/hooks/use-operator";

function StatCard({
  title,
  value,
  loading,
}: {
  title: string;
  value: number;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
      </CardContent>
    </Card>
  );
}

export default function OperatorDashboard() {
  const devicesQuery = useOperatorDevices(undefined, 500, 0);
  const alertsQuery = useOperatorAlerts("OPEN", undefined, 20);
  const quarantineQuery = useQuarantine(60, 20);

  const devices = devicesQuery.data?.devices || [];
  const alerts = alertsQuery.data?.alerts || [];
  const quarantine = quarantineQuery.data?.events || [];

  const totals = useMemo(() => {
    const totalDevices = devices.length;
    const onlineDevices = devices.filter((d) => d.status === "ONLINE").length;
    const openAlerts = alertsQuery.data?.alerts?.length || 0;
    const quarantineCount = quarantineQuery.data?.events?.length || 0;
    return { totalDevices, onlineDevices, openAlerts, quarantineCount };
  }, [devices, alertsQuery.data, quarantineQuery.data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operator Dashboard"
        description="Cross-tenant system overview"
      />

      <WidgetErrorBoundary widgetName="Operator Stats">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Devices"
            value={totals.totalDevices}
            loading={devicesQuery.isLoading}
          />
          <StatCard
            title="Online Devices"
            value={totals.onlineDevices}
            loading={devicesQuery.isLoading}
          />
          <StatCard
            title="Open Alerts"
            value={totals.openAlerts}
            loading={alertsQuery.isLoading}
          />
          <StatCard
            title="Quarantine Events"
            value={totals.quarantineCount}
            loading={quarantineQuery.isLoading}
          />
        </div>
      </WidgetErrorBoundary>

      <div className="grid gap-6 lg:grid-cols-2">
        <WidgetErrorBoundary widgetName="Open Alerts">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Recent Open Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              {alertsQuery.error ? (
                <div className="text-destructive text-sm">
                  Failed to load alerts: {(alertsQuery.error as Error).message}
                </div>
              ) : alertsQuery.isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-8 w-full" />
                  ))}
                </div>
              ) : alerts.length === 0 ? (
                <div className="text-sm text-muted-foreground">No open alerts.</div>
              ) : (
                <div className="rounded-md border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Tenant</TableHead>
                        <TableHead>Device</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Severity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {alerts.slice(0, 10).map((a) => (
                        <TableRow key={a.alert_id}>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {a.created_at}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {a.tenant_id}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {a.device_id}
                          </TableCell>
                          <TableCell className="text-xs">{a.alert_type}</TableCell>
                          <TableCell>
                            <SeverityBadge severity={a.severity} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </WidgetErrorBoundary>

        <WidgetErrorBoundary widgetName="Quarantine Events">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Recent Quarantine Events</CardTitle>
            </CardHeader>
            <CardContent>
              {quarantineQuery.error ? (
                <div className="text-destructive text-sm">
                  Failed to load quarantine: {(quarantineQuery.error as Error).message}
                </div>
              ) : quarantineQuery.isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-8 w-full" />
                  ))}
                </div>
              ) : quarantine.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No quarantine events in the last hour.
                </div>
              ) : (
                <div className="rounded-md border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Tenant</TableHead>
                        <TableHead>Device</TableHead>
                        <TableHead>Reason</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {quarantine.slice(0, 10).map((q, idx) => (
                        <TableRow key={`${q.device_id}-${q.ingested_at}-${idx}`}>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {q.ingested_at}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {q.tenant_id}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {q.device_id}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {q.reason}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}

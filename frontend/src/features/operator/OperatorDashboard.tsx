import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AlertTriangle, Building2, Grid3X3, Monitor, Server } from "lucide-react";
import { fetchOperatorAlerts } from "@/services/api/operator";
import { fetchSystemAggregates, fetchSystemErrors, fetchSystemHealth } from "@/services/api/system";

function kpiCard(title: string, value: string, sub: string) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-sm uppercase tracking-wide text-muted-foreground">{title}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{sub}</div>
    </div>
  );
}

function navCard(to: string, title: string, description: string, icon: React.ElementType) {
  const Icon = icon;
  return (
    <Link
      to={to}
      className="rounded-lg border bg-card p-4 transition-colors hover:border-primary hover:bg-muted/50"
    >
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-4 w-4 text-primary" />
        <div className="font-semibold">{title}</div>
      </div>
      <div className="text-sm text-muted-foreground">{description}</div>
      <div className="mt-3 text-sm font-medium text-primary">Open -&gt;</div>
    </Link>
  );
}

export default function OperatorDashboard() {
  const { data: health } = useQuery({
    queryKey: ["operator-dashboard-health"],
    queryFn: fetchSystemHealth,
    refetchInterval: 30000,
  });
  const { data: aggregates } = useQuery({
    queryKey: ["operator-dashboard-aggregates"],
    queryFn: fetchSystemAggregates,
    refetchInterval: 30000,
  });
  const { data: alerts } = useQuery({
    queryKey: ["operator-dashboard-open-alerts"],
    queryFn: () => fetchOperatorAlerts("OPEN", undefined, 200),
    refetchInterval: 30000,
  });
  const { data: errors } = useQuery({
    queryKey: ["operator-dashboard-errors"],
    queryFn: () => fetchSystemErrors(1),
    refetchInterval: 30000,
  });

  const lastUpdated = useMemo(() => new Date().toLocaleTimeString(), [health?.checked_at]);
  const online = aggregates?.devices.online ?? 0;
  const totalDevices = aggregates?.devices.registered ?? 0;
  const onlinePct = totalDevices > 0 ? Math.round((online / totalDevices) * 100) : 0;
  const openAlerts = aggregates?.alerts.open ?? 0;
  const criticalCount =
    alerts?.alerts.filter((a) => (a.severity ?? 0) >= 4).length ?? 0;
  const highCount =
    alerts?.alerts.filter((a) => (a.severity ?? 0) === 3).length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-2xl font-semibold">Operator Console</div>
          <div className="text-sm text-muted-foreground">
            <span
              className={`mr-2 inline-block h-2 w-2 rounded-full ${
                health?.status === "healthy" ? "bg-status-online" : "bg-status-warning"
              }`}
            />
            {health?.status?.toUpperCase() ?? "UNKNOWN"} | Last: {lastUpdated}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {kpiCard(
          "Tenants",
          String(aggregates?.tenants.active ?? 0),
          `${aggregates?.tenants.total ?? 0} total`
        )}
        {kpiCard("Devices", `${online}/${totalDevices}`, `${onlinePct}% online`)}
        {kpiCard("Alerts", String(openAlerts), `${criticalCount} critical, ${highCount} high`)}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {navCard("/operator/noc", "NOC Console", "Full system monitoring wallboard", Monitor)}
        {navCard(
          "/operator/tenant-matrix",
          "Tenant Health Matrix",
          "All tenant health at a glance",
          Grid3X3
        )}
        {navCard("/operator/tenants", "Tenants", "Manage tenant records and status", Building2)}
        {navCard("/operator/system", "System Alerts", "Investigate system-level incidents", AlertTriangle)}
      </div>

      <div className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <Server className="h-4 w-4 text-muted-foreground" />
          <div className="font-medium">Recent Errors (last hour)</div>
        </div>
        <div className="space-y-1 text-sm">
          {(errors?.errors ?? []).slice(0, 5).map((err, idx) => (
            <div key={`${err.timestamp}-${idx}`} className="flex items-start gap-2">
              <span className="text-muted-foreground">
                {new Date(err.timestamp).toLocaleTimeString()}
              </span>
              <span className="font-medium text-red-500">{err.error_type}</span>
              <span className="text-muted-foreground">
                {err.tenant_id ? `tenant: ${err.tenant_id}` : "system"}
              </span>
            </div>
          ))}
          {(errors?.errors ?? []).length === 0 && (
            <div className="text-muted-foreground">No recent errors.</div>
          )}
        </div>
      </div>
    </div>
  );
}

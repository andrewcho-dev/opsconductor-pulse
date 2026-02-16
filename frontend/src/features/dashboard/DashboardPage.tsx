import { PageHeader } from "@/components/shared";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { AlertTrendWidget, DeviceStatusWidget, FleetHealthWidget } from "./widgets";
import { UptimeSummaryWidget } from "@/features/devices/UptimeSummaryWidget";
import FleetKpiStrip from "./FleetKpiStrip";
import { useAlerts } from "@/hooks/use-alerts";
import { acknowledgeAlert } from "@/services/api/alerts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";
import type { DeviceListResponse } from "@/services/api/types";
import { Link } from "react-router-dom";
import { useAuth } from "@/services/auth/AuthProvider";

function relativeTime(input?: string | null) {
  if (!input) return "never";
  const diffMs = Date.now() - new Date(input).getTime();
  if (!Number.isFinite(diffMs) || diffMs < 0) return "just now";
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function statusDot(status: string) {
  if (status === "ONLINE") return "bg-green-500";
  if (status === "STALE") return "bg-yellow-500";
  return "bg-red-500";
}

function ActiveAlertsPanel() {
  const { data } = useAlerts("OPEN", 50, 0);
  const queryClient = useQueryClient();
  const ackMutation = useMutation({
    mutationFn: (alertId: number) => acknowledgeAlert(String(alertId)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const alerts = [...(data?.alerts ?? [])]
    .sort((a, b) => b.severity - a.severity)
    .slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Active Alerts</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No open alerts.</p>
        ) : (
          alerts.map((alert) => (
            <div key={alert.alert_id} className="rounded-md border border-border p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">S{alert.severity}</Badge>
                    <span className="text-sm font-medium">{alert.device_id}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {alert.alert_type} · {relativeTime(alert.created_at)}
                  </p>
                </div>
                <button
                  onClick={() => ackMutation.mutate(alert.alert_id)}
                  disabled={ackMutation.isPending}
                  className="rounded border border-border px-2 py-1 text-xs hover:bg-accent disabled:opacity-60"
                >
                  Acknowledge
                </button>
              </div>
            </div>
          ))
        )}
        <Link to="/alerts" className="block text-sm text-primary hover:underline">
          View all alerts →
        </Link>
      </CardContent>
    </Card>
  );
}

function RecentlyActiveDevicesPanel() {
  const { data } = useQuery({
    queryKey: ["dashboard-recent-devices"],
    queryFn: () => apiGet<DeviceListResponse>("/api/v2/devices?limit=5&sort=last_seen"),
    refetchInterval: 30000,
  });
  const devices = [...(data?.devices ?? [])]
    .sort((a, b) => {
      const aTs = a.last_seen_at ? new Date(a.last_seen_at).getTime() : 0;
      const bTs = b.last_seen_at ? new Date(b.last_seen_at).getTime() : 0;
      return bTs - aTs;
    })
    .slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recently Active Devices</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {devices.length === 0 ? (
          <p className="text-sm text-muted-foreground">No devices found.</p>
        ) : (
          devices.map((device) => (
            <div key={device.device_id} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${statusDot(device.status)}`} />
                <span className="text-sm font-medium">{device.device_id}</span>
              </div>
              <span className="text-xs text-muted-foreground">
                {relativeTime(device.last_seen_at)}
              </span>
            </div>
          ))
        )}
        <Link to="/devices" className="block text-sm text-primary hover:underline">
          View all devices →
        </Link>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [now, setNow] = useState(Date.now());
  const [lastUpdated, setLastUpdated] = useState(Date.now());
  const subtitle = user?.tenantId ? `Tenant: ${user.tenantId}` : "Real-time operational view";

  useEffect(() => {
    const refreshTimer = window.setInterval(() => setLastUpdated(Date.now()), 30000);
    const clockTimer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      window.clearInterval(refreshTimer);
      window.clearInterval(clockTimer);
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Fleet Overview"
        description={subtitle}
        action={
          <div className="text-xs text-muted-foreground">
            Last updated: {Math.max(0, Math.round((now - lastUpdated) / 1000))}s ago
          </div>
        }
      />

      <WidgetErrorBoundary widgetName="Fleet KPI Strip">
        <FleetKpiStrip />
      </WidgetErrorBoundary>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WidgetErrorBoundary widgetName="Fleet Uptime">
            <UptimeSummaryWidget />
          </WidgetErrorBoundary>
        </div>
        <WidgetErrorBoundary widgetName="Fleet Health">
          <FleetHealthWidget />
        </WidgetErrorBoundary>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <WidgetErrorBoundary widgetName="Active Alerts">
          <ActiveAlertsPanel />
        </WidgetErrorBoundary>
        <WidgetErrorBoundary widgetName="Device Status">
          <DeviceStatusWidget />
        </WidgetErrorBoundary>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <WidgetErrorBoundary widgetName="Alert Trend">
          <AlertTrendWidget />
        </WidgetErrorBoundary>
        <WidgetErrorBoundary widgetName="Recently Active Devices">
          <RecentlyActiveDevicesPanel />
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}

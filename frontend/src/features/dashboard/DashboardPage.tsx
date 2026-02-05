import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { useAlerts } from "@/hooks/use-alerts";
import { Skeleton } from "@/components/ui/skeleton";
import { Cpu, Wifi, AlertTriangle, Bell } from "lucide-react";

function StatCard({
  title,
  value,
  icon: Icon,
  loading,
  className,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  loading?: boolean;
  className?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 ${className || "text-muted-foreground"}`} />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <div className="text-3xl font-bold">{value}</div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: deviceData, isLoading: devicesLoading } = useDevices(500, 0);
  const { data: alertData, isLoading: alertsLoading } = useAlerts("OPEN", 100, 0);

  const devices = deviceData?.devices || [];
  const alerts = alertData?.alerts || [];

  const totalDevices = devices.length;
  const onlineDevices = devices.filter((d) => d.status === "ONLINE").length;
  const staleDevices = devices.filter((d) => d.status === "STALE").length;
  const openAlerts = alerts.length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Real-time overview of your IoT fleet"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Devices"
          value={totalDevices}
          icon={Cpu}
          loading={devicesLoading}
        />
        <StatCard
          title="Online"
          value={onlineDevices}
          icon={Wifi}
          loading={devicesLoading}
          className="text-green-400"
        />
        <StatCard
          title="Stale"
          value={staleDevices}
          icon={AlertTriangle}
          loading={devicesLoading}
          className="text-orange-400"
        />
        <StatCard
          title="Open Alerts"
          value={openAlerts}
          icon={Bell}
          loading={alertsLoading}
          className="text-red-400"
        />
      </div>

      {/* Recent alerts summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          {alertsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open alerts.</p>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 5).map((a) => (
                <div
                  key={a.alert_id}
                  className="flex items-center justify-between text-sm border-b border-border pb-2 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        a.severity >= 5
                          ? "bg-red-500"
                          : a.severity >= 3
                          ? "bg-orange-500"
                          : "bg-blue-500"
                      }`}
                    />
                    <span className="font-mono text-xs text-muted-foreground">
                      {a.device_id}
                    </span>
                    <span>{a.summary}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {a.alert_type}
                  </span>
                </div>
              ))}
              {alerts.length > 5 && (
                <p className="text-xs text-muted-foreground pt-1">
                  + {alerts.length - 5} more alerts
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDevices } from "@/hooks/use-devices";
import { useAlertStore } from "@/stores/alert-store";
import { useAlerts } from "@/hooks/use-alerts";
import { Cpu, Wifi, AlertTriangle, Bell } from "lucide-react";
import { memo } from "react";

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

function StatCardsWidgetInner() {
  const { data: deviceData, isLoading: devicesLoading } = useDevices(500, 0);

  // For alert count, prefer live WS data if available, fallback to REST
  const hasWsData = useAlertStore((s) => s.hasWsData);
  const liveAlerts = useAlertStore((s) => s.liveAlerts);
  const { data: alertData, isLoading: alertsLoading } = useAlerts("OPEN", 100, 0);

  const devices = deviceData?.devices || [];
  const totalDevices = devices.length;
  const onlineDevices = devices.filter((d) => d.status === "ONLINE").length;
  const staleDevices = devices.filter((d) => d.status === "STALE").length;

  // Use WS alert count if available, otherwise REST
  const openAlerts = hasWsData ? liveAlerts.length : (alertData?.alerts?.length || 0);
  const alertsReady = hasWsData || !alertsLoading;

  return (
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
        className="text-green-700 dark:text-green-400"
      />
      <StatCard
        title="Stale"
        value={staleDevices}
        icon={AlertTriangle}
        loading={devicesLoading}
        className="text-orange-700 dark:text-orange-400"
      />
      <StatCard
        title="Open Alerts"
        value={openAlerts}
        icon={Bell}
        loading={!alertsReady}
        className="text-red-700 dark:text-red-400"
      />
    </div>
  );
}

export const StatCardsWidget = memo(StatCardsWidgetInner);

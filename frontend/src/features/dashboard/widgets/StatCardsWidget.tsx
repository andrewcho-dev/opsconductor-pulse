import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Cpu, Wifi, AlertTriangle, Bell } from "lucide-react";
import { memo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchFleetSummary } from "@/services/api/devices";

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
  const { data: summary, isLoading } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 10_000,
  });

  const totalDevices = summary?.total_devices ?? summary?.total ?? 0;
  const onlineDevices = summary?.online ?? summary?.ONLINE ?? 0;
  const staleDevices = summary?.stale ?? summary?.STALE ?? 0;
  const openAlerts = summary?.alerts_open ?? 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Devices"
        value={totalDevices}
        icon={Cpu}
        loading={isLoading}
      />
      <StatCard
        title="Online"
        value={onlineDevices}
        icon={Wifi}
        loading={isLoading}
        className="text-green-700 dark:text-green-400"
      />
      <StatCard
        title="Stale"
        value={staleDevices}
        icon={AlertTriangle}
        loading={isLoading}
        className="text-orange-700 dark:text-orange-400"
      />
      <StatCard
        title="Open Alerts"
        value={openAlerts}
        icon={Bell}
        loading={isLoading}
        className="text-red-700 dark:text-red-400"
      />
    </div>
  );
}

export const StatCardsWidget = memo(StatCardsWidgetInner);

import type { ElementType } from "react";
import { memo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchFleetSummary } from "@/services/api/devices";
import { Activity, AlertTriangle, Battery, Clock, Wifi } from "lucide-react";

function FleetHealthWidgetInner() {
  const { data, isLoading } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 10_000,
  });

  if (isLoading || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4" />
            Fleet Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const onlinePct =
    data.total_devices > 0
      ? Math.round((data.online / data.total_devices) * 100)
      : 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4" />
          Fleet Health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatusCard
            icon={Wifi}
            label="Online"
            value={`${data.online}/${data.total_devices}`}
            subtext={`${onlinePct}%`}
            status={onlinePct >= 95 ? "success" : onlinePct >= 80 ? "warning" : "error"}
          />

          <Link to="/alerts?status=open" className="block">
            <StatusCard
              icon={AlertTriangle}
              label="Open Alerts"
              value={data.alerts_open.toString()}
              subtext={data.alerts_new_1h > 0 ? `▲ ${data.alerts_new_1h} new/1h` : "—"}
              status={data.alerts_open > 0 ? "error" : "success"}
            />
          </Link>

          <StatusCard
            icon={Battery}
            label="Low Battery"
            value={data.low_battery_count.toString()}
            subtext={`< ${data.low_battery_threshold}%`}
            status={data.low_battery_count > 0 ? "warning" : "success"}
            tooltip={
              data.low_battery_devices.length > 0
                ? data.low_battery_devices.join(", ")
                : undefined
            }
          />

          <Link to="/devices?state=stale" className="block">
            <StatusCard
              icon={Clock}
              label="Stale"
              value={data.stale.toString()}
              subtext="> 5 min"
              status={data.stale > 0 ? "warning" : "success"}
            />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

interface StatusCardProps {
  icon: ElementType;
  label: string;
  value: string;
  subtext: string;
  status: "success" | "warning" | "error";
  tooltip?: string;
}

function StatusCard({ icon: Icon, label, value, subtext, status, tooltip }: StatusCardProps) {
  const colors = {
    success: "text-green-600 dark:text-green-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    error: "text-red-600 dark:text-red-400",
  };

  const bgColors = {
    success: "bg-green-50 dark:bg-green-950",
    warning: "bg-yellow-50 dark:bg-yellow-950",
    error: "bg-red-50 dark:bg-red-950",
  };

  return (
    <div
      className={`rounded-lg p-3 transition hover:opacity-80 ${bgColors[status]}`}
      title={tooltip}
    >
      <div className="mb-1 flex items-center gap-2">
        <Icon className={`h-4 w-4 ${colors[status]}`} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className={`text-2xl font-bold ${colors[status]}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{subtext}</div>
    </div>
  );
}

export const FleetHealthWidget = memo(FleetHealthWidgetInner);

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchFleetSummary, getFleetUptimeSummary } from "@/services/api/devices";
import { fetchAlerts, fetchMaintenanceWindows } from "@/services/api/alerts";
import type { WidgetRendererProps } from "../widget-registry";

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "0";
  return value.toLocaleString();
}

function maintenanceActiveCount(
  windows: Array<{
    starts_at: string;
    ends_at: string | null;
    enabled?: boolean;
    is_active?: boolean;
  }>
) {
  const now = Date.now();
  return windows.filter((w) => {
    if (w.enabled === false) return false;
    if (typeof w.is_active === "boolean") return w.is_active;
    const startsAt = Date.parse(w.starts_at);
    const endsAt = w.ends_at ? Date.parse(w.ends_at) : Number.POSITIVE_INFINITY;
    if (Number.isNaN(startsAt)) return false;
    return startsAt <= now && now <= endsAt;
  }).length;
}

export default function KpiTileRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "device_count";

  const needsFleet = ["device_count", "online_count", "offline_count"].includes(metric);
  const needsAlerts = metric === "alert_count";
  const needsUptime = metric === "uptime_pct";
  const needsMaintenance = metric === "maintenance_active";

  const { data: fleetSummary, isLoading: fleetLoading } = useQuery({
    queryKey: ["widget-kpi", "fleet-summary"],
    queryFn: fetchFleetSummary,
    enabled: needsFleet,
    refetchInterval: 30000,
  });

  const { data: alertData, isLoading: alertLoading } = useQuery({
    queryKey: ["widget-kpi", "alerts-open"],
    queryFn: () => fetchAlerts("OPEN", 1, 0),
    enabled: needsAlerts,
    refetchInterval: 30000,
  });

  const { data: uptimeData, isLoading: uptimeLoading } = useQuery({
    queryKey: ["widget-kpi", "uptime"],
    queryFn: getFleetUptimeSummary,
    enabled: needsUptime,
    refetchInterval: 30000,
  });

  const { data: maintenanceData, isLoading: maintenanceLoading } = useQuery({
    queryKey: ["widget-kpi", "maintenance"],
    queryFn: fetchMaintenanceWindows,
    enabled: needsMaintenance,
    refetchInterval: 30000,
  });

  const isLoading = fleetLoading || alertLoading || uptimeLoading || maintenanceLoading;

  const value = useMemo(() => {
    if (metric === "device_count") {
      const total =
        fleetSummary?.total ??
        fleetSummary?.total_devices ??
        ((fleetSummary?.ONLINE ?? 0) +
          (fleetSummary?.STALE ?? 0) +
          (fleetSummary?.OFFLINE ?? 0));
      return formatNumber(total ?? 0);
    }
    if (metric === "online_count") {
      const online = fleetSummary?.online ?? fleetSummary?.ONLINE ?? 0;
      return formatNumber(online);
    }
    if (metric === "offline_count") {
      const offline = fleetSummary?.offline ?? fleetSummary?.OFFLINE ?? 0;
      return formatNumber(offline);
    }
    if (metric === "alert_count") {
      return formatNumber(alertData?.total ?? 0);
    }
    if (metric === "uptime_pct") {
      const pct = uptimeData?.avg_uptime_pct ?? 0;
      return `${pct.toFixed(1)}%`;
    }
    if (metric === "maintenance_active") {
      return formatNumber(maintenanceActiveCount(maintenanceData?.windows ?? []));
    }
    return "—";
  }, [metric, fleetSummary, alertData, uptimeData, maintenanceData]);

  if (isLoading) {
    return <Skeleton className="h-16 w-full" />;
  }

  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="text-3xl font-bold">{value}</div>
        <div className="text-xs text-muted-foreground mt-1">{metric}</div>
      </div>
    </div>
  );
}


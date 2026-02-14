import { useQuery } from "@tanstack/react-query";
import {
  Cpu,
  Wifi,
  WifiOff,
  Gauge,
  Bell,
  CalendarOff,
} from "lucide-react";
import { fetchFleetSummary, getFleetUptimeSummary } from "@/services/api/devices";
import { fetchAlerts, fetchMaintenanceWindows } from "@/services/api/alerts";

function formatCount(value: number) {
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

export default function FleetKpiStrip() {
  const { data: fleetSummary } = useQuery({
    queryKey: ["fleet-kpi-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 30000,
  });
  const { data: alertData } = useQuery({
    queryKey: ["fleet-kpi-open-alerts"],
    queryFn: () => fetchAlerts("OPEN", 1, 0),
    refetchInterval: 30000,
  });
  const { data: maintenanceData } = useQuery({
    queryKey: ["fleet-kpi-maintenance"],
    queryFn: fetchMaintenanceWindows,
    refetchInterval: 30000,
  });
  const { data: uptimeData } = useQuery({
    queryKey: ["fleet-kpi-uptime"],
    queryFn: getFleetUptimeSummary,
    refetchInterval: 30000,
  });

  const total =
    fleetSummary?.total ??
    fleetSummary?.total_devices ??
    ((fleetSummary?.ONLINE ?? 0) +
      (fleetSummary?.STALE ?? 0) +
      (fleetSummary?.OFFLINE ?? 0));
  const online = fleetSummary?.online ?? fleetSummary?.ONLINE ?? 0;
  const offline = fleetSummary?.offline ?? fleetSummary?.OFFLINE ?? 0;
  const uptimePct = uptimeData?.avg_uptime_pct ?? 0;
  const openAlerts = alertData?.total ?? 0;
  const activeMaintenance = maintenanceActiveCount(maintenanceData?.windows ?? []);
  const uptimeBorder =
    uptimePct >= 99 ? "border-l-green-500" : uptimePct >= 95 ? "border-l-yellow-500" : "border-l-red-500";

  const cards = [
    {
      key: "total",
      label: "Total Devices",
      value: formatCount(total),
      border: "border-l-slate-500",
      icon: Cpu,
      iconColor: "text-slate-500",
    },
    {
      key: "online",
      label: "Online",
      value: formatCount(online),
      border: "border-l-green-500",
      icon: Wifi,
      iconColor: "text-green-500",
    },
    {
      key: "offline",
      label: "Offline",
      value: formatCount(offline),
      border: offline > 0 ? "border-l-red-500" : "border-l-slate-400",
      icon: WifiOff,
      iconColor: offline > 0 ? "text-red-500" : "text-slate-400",
    },
    {
      key: "uptime",
      label: "Fleet Uptime %",
      value: `${uptimePct.toFixed(1)}%`,
      border: uptimeBorder,
      icon: Gauge,
      iconColor:
        uptimePct >= 99 ? "text-green-500" : uptimePct >= 95 ? "text-yellow-500" : "text-red-500",
    },
    {
      key: "alerts",
      label: "Open Alerts",
      value: formatCount(openAlerts),
      border: openAlerts > 0 ? "border-l-red-500" : "border-l-slate-400",
      icon: Bell,
      iconColor: openAlerts > 0 ? "text-red-500" : "text-slate-400",
    },
    {
      key: "maintenance",
      label: "Active Maintenance",
      value: formatCount(activeMaintenance),
      border: "border-l-blue-500",
      icon: CalendarOff,
      iconColor: "text-blue-500",
    },
  ];

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
      {cards.map((card) => (
        <div
          key={card.key}
          className={`rounded-lg border border-border border-l-4 p-4 ${card.border}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{card.label}</span>
            <card.icon className={`h-4 w-4 ${card.iconColor}`} />
          </div>
          <div className="mt-1 text-3xl font-bold">{card.value}</div>
        </div>
      ))}
    </div>
  );
}

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Maximize2, Pause, Play } from "lucide-react";
import { fetchSystemAggregates, fetchSystemHealth } from "@/services/api/system";
import { AlertHeatmap } from "./AlertHeatmap";
import { GaugeRow } from "./GaugeRow";
import { LiveEventFeed } from "./LiveEventFeed";
import { MetricsChartGrid } from "./MetricsChartGrid";
import { ServiceTopologyStrip } from "./ServiceTopologyStrip";

function statusDotClass(status: string) {
  if (status === "healthy") return "bg-green-500";
  if (status === "degraded") return "bg-yellow-500";
  if (status === "down") return "bg-red-500";
  return "bg-gray-500";
}

export default function NOCPage() {
  const [refreshInterval, setRefreshInterval] = useState(15000);
  const [isPaused, setIsPaused] = useState(false);

  const { data: health } = useQuery({
    queryKey: ["noc-system-health-header"],
    queryFn: fetchSystemHealth,
    refetchInterval: isPaused ? false : refreshInterval,
  });

  const { data: aggregates } = useQuery({
    queryKey: ["noc-system-aggregates-header"],
    queryFn: fetchSystemAggregates,
    refetchInterval: isPaused ? false : refreshInterval,
  });

  const systemStatus = health?.status ?? "unknown";
  const lastUpdated = useMemo(() => new Date().toLocaleTimeString(), [health?.checked_at]);

  const enterFullscreen = () => {
    document.documentElement.requestFullscreen?.();
  };

  return (
    <div className="min-h-screen space-y-4 bg-gray-950 p-4 text-gray-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-wider text-gray-100">NOC</span>
            <span className={`inline-block h-2 w-2 rounded-full ${statusDotClass(systemStatus)}`} />
            <span className="text-sm text-gray-400">{systemStatus.toUpperCase()}</span>
          </div>
          <div className="text-xs text-gray-500">
            Last updated: {lastUpdated} | {aggregates?.tenants.active ?? 0} tenants |{" "}
            {aggregates?.devices.registered ?? 0} devices
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300"
          >
            <option value={15000}>15s</option>
            <option value={30000}>30s</option>
            <option value={60000}>60s</option>
          </select>
          <button
            onClick={() => setIsPaused((prev) => !prev)}
            title="Pause/Resume"
            className="rounded border border-gray-600 bg-gray-800 p-1.5 text-gray-300 hover:bg-gray-700"
          >
            {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </button>
          <button
            onClick={enterFullscreen}
            title="Fullscreen"
            className="rounded border border-gray-600 bg-gray-800 p-1.5 text-gray-300 hover:bg-gray-700"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <GaugeRow refreshInterval={refreshInterval} isPaused={isPaused} />
      <MetricsChartGrid refreshInterval={refreshInterval} isPaused={isPaused} />
      <ServiceTopologyStrip refreshInterval={refreshInterval} isPaused={isPaused} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <AlertHeatmap refreshInterval={refreshInterval} isPaused={isPaused} />
        <LiveEventFeed refreshInterval={10000} isPaused={isPaused} />
      </div>
    </div>
  );
}

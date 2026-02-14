import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Maximize2, Minimize2, Pause, Play } from "lucide-react";
import { fetchSystemAggregates, fetchSystemHealth } from "@/services/api/system";
import { AlertHeatmap } from "./AlertHeatmap";
import { GaugeRow } from "./GaugeRow";
import { LiveEventFeed } from "./LiveEventFeed";
import { MetricsChartGrid } from "./MetricsChartGrid";
import { NOC_COLORS } from "./nocColors";
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
  const [tvMode, setTvMode] = useState(false);

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

  const toggleTvMode = useCallback(() => {
    if (!tvMode) {
      document.documentElement.requestFullscreen?.().catch(() => {});
      setTvMode(true);
    } else {
      document.exitFullscreen?.().catch(() => {});
      setTvMode(false);
    }
  }, [tvMode]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.key === "f" || e.key === "F") && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        toggleTvMode();
      }
      if (e.key === "Escape" && tvMode) {
        setTvMode(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleTvMode, tvMode]);

  useEffect(() => {
    const handler = () => {
      if (!document.fullscreenElement) {
        setTvMode(false);
      }
    };
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  useEffect(() => {
    if (tvMode) {
      document.body.classList.add("noc-tv-mode");
    } else {
      document.body.classList.remove("noc-tv-mode");
    }
    return () => document.body.classList.remove("noc-tv-mode");
  }, [tvMode]);

  return (
    <div className="min-h-screen space-y-4 p-4 text-gray-100" style={{ backgroundColor: NOC_COLORS.bg.page }}>
      {tvMode && (
        <div className="fixed right-2 top-2 z-50 rounded bg-gray-800/80 px-2 py-1 text-xs text-gray-400">
          TV MODE - Press F to exit
        </div>
      )}
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
            onClick={toggleTvMode}
            title="TV Mode (F)"
            className="rounded border border-gray-600 bg-gray-800 p-1.5 text-gray-300 hover:bg-gray-700"
          >
            {tvMode ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
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

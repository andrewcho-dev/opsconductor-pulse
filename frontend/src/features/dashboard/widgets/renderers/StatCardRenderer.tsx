import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import {
  fetchFleetSummary,
  getFleetUptimeSummary,
  fetchTelemetryHistory,
} from "@/services/api/devices";
import { fetchAlerts } from "@/services/api/alerts";
import { useUIStore } from "@/stores/ui-store";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { WidgetRendererProps } from "../widget-registry";

export default function StatCardRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "device_count";
  const decimalPrecision = (config.decimal_precision as number | undefined) ?? 1;
  const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];
  const isDark = useUIStore((s) => s.resolvedTheme === "dark");

  const needsFleet = ["device_count", "online_count", "offline_count"].includes(metric);
  const needsAlerts = metric === "alert_count";
  const needsUptime = metric === "uptime_pct";

  const { data: fleetSummary, isLoading: fleetLoading } = useQuery({
    queryKey: ["widget-stat", "fleet-summary"],
    queryFn: fetchFleetSummary,
    enabled: needsFleet,
    refetchInterval: 30000,
  });

  const { data: alertData, isLoading: alertLoading } = useQuery({
    queryKey: ["widget-stat", "alerts-open"],
    queryFn: () => fetchAlerts("OPEN", 1, 0),
    enabled: needsAlerts,
    refetchInterval: 30000,
  });

  const { data: uptimeData, isLoading: uptimeLoading } = useQuery({
    queryKey: ["widget-stat", "uptime"],
    queryFn: getFleetUptimeSummary,
    enabled: needsUptime,
    refetchInterval: 30000,
  });

  // Optional: sparkline device metric history (if configured)
  const sparklineDeviceId =
    typeof config.sparkline_device === "string" ? (config.sparkline_device as string) : undefined;
  const { data: historyData } = useQuery({
    queryKey: ["widget-stat-sparkline", sparklineDeviceId, metric],
    queryFn: () => fetchTelemetryHistory(sparklineDeviceId!, metric, "24h"),
    enabled: !!sparklineDeviceId,
    refetchInterval: 60000,
  });

  const isLoading = fleetLoading || alertLoading || uptimeLoading;

  const numericValue = useMemo(() => {
    if (metric === "device_count") {
      const total =
        fleetSummary?.total ??
        fleetSummary?.total_devices ??
        ((fleetSummary?.ONLINE ?? 0) + (fleetSummary?.STALE ?? 0) + (fleetSummary?.OFFLINE ?? 0));
      return total ?? 0;
    }
    if (metric === "online_count") return fleetSummary?.online ?? fleetSummary?.ONLINE ?? 0;
    if (metric === "offline_count") return fleetSummary?.offline ?? fleetSummary?.OFFLINE ?? 0;
    if (metric === "alert_count") return alertData?.total ?? 0;
    if (metric === "uptime_pct") return uptimeData?.avg_uptime_pct ?? 0;
    return null;
  }, [metric, fleetSummary, alertData, uptimeData]);

  const formatted = useMemo(() => {
    if (numericValue == null) return "—";
    if (metric === "uptime_pct") return `${numericValue.toFixed(decimalPrecision)}%`;
    return numericValue.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimalPrecision,
    });
  }, [decimalPrecision, metric, numericValue]);

  const trend = useMemo(() => {
    const points = (historyData as { points?: Array<{ avg?: number | null }> } | undefined)?.points ?? [];
    if (points.length < 2) return { direction: "flat" as const, pct: 0 };
    const recent = points.slice(-Math.ceil(points.length / 4));
    const earlier = points.slice(0, Math.ceil(points.length / 4));
    const avgRecent = recent.reduce((s, p) => s + (p.avg ?? 0), 0) / Math.max(1, recent.length);
    const avgEarlier = earlier.reduce((s, p) => s + (p.avg ?? 0), 0) / Math.max(1, earlier.length);
    if (avgEarlier === 0) return { direction: "flat" as const, pct: 0 };
    const pct = ((avgRecent - avgEarlier) / Math.abs(avgEarlier)) * 100;
    if (pct > 1) return { direction: "up" as const, pct };
    if (pct < -1) return { direction: "down" as const, pct };
    return { direction: "flat" as const, pct };
  }, [historyData]);

  const sparklineOption = useMemo<EChartsOption>(() => {
    const points = (historyData as { points?: Array<{ avg?: number | null; max?: number | null; min?: number | null }> } | undefined)
      ?.points ?? [];
    const y = points.map((p) => p.avg ?? p.max ?? p.min ?? null);
    const color = isDark ? "rgba(59,130,246,0.5)" : "rgba(59,130,246,0.3)";
    return {
      grid: { left: 0, right: 0, top: 0, bottom: 0 },
      xAxis: { type: "category", show: false, data: y.map((_, i) => i) },
      yAxis: { type: "value", show: false },
      series: [
        {
          type: "line",
          data: y,
          showSymbol: false,
          smooth: true,
          lineStyle: { width: 1.5, color: isDark ? "#3b82f6" : "#93c5fd" },
          areaStyle: {
            opacity: 1,
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color },
                { offset: 1, color: "rgba(0,0,0,0)" },
              ],
            },
          },
        },
      ],
    };
  }, [historyData, isDark]);

  const thresholdColor = useMemo(() => {
    if (thresholds.length === 0 || numericValue == null) return undefined;
    const sorted = [...thresholds].sort((a, b) => b.value - a.value);
    return sorted.find((t) => numericValue >= t.value)?.color;
  }, [numericValue, thresholds]);

  if (isLoading) return <Skeleton className="h-16 w-full" />;

  const hasSparkline =
    (((historyData as { points?: unknown[] } | undefined)?.points ?? []) as unknown[]).length > 1;

  return (
    <div className="h-full flex flex-col items-center justify-center relative overflow-hidden">
      {hasSparkline && (
        <div className="absolute inset-x-0 bottom-0 h-1/2 opacity-60 pointer-events-none">
          <EChartWrapper option={sparklineOption} style={{ width: "100%", height: "100%" }} />
        </div>
      )}

      <div className="relative z-10 text-center">
        <div
          className="text-2xl font-semibold"
          style={thresholdColor ? { color: thresholdColor } : undefined}
        >
          {formatted}
        </div>
        <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground mt-0.5">
          <span>{metric.replace(/_/g, " ")}</span>
          {hasSparkline && (
            <span className="flex items-center gap-0.5 ml-1">
              {trend.direction === "up" && <TrendingUp className="h-3 w-3 text-green-500" />}
              {trend.direction === "down" && (
                <TrendingDown className="h-3 w-3 text-red-500" />
              )}
              {trend.direction === "flat" && <Minus className="h-3 w-3 text-muted-foreground" />}
              {trend.pct !== 0 && (
                <span
                  className={
                    trend.direction === "up"
                      ? "text-green-500"
                      : trend.direction === "down"
                        ? "text-red-500"
                        : ""
                  }
                >
                  {Math.abs(trend.pct).toFixed(1)}%
                </span>
              )}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}


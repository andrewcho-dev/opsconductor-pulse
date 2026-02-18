import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { runAnalyticsQuery, type AnalyticsQueryResponse } from "@/services/api/analytics";
import { CHART_COLORS } from "@/lib/charts/colors";
import { useUIStore } from "@/stores/ui-store";
import type { WidgetRendererProps } from "../widget-registry";

const VALID_RANGES = ["1h", "6h", "24h", "7d", "30d"] as const;
type Range = (typeof VALID_RANGES)[number];

function asRange(value: unknown, fallback: Range): Range {
  return VALID_RANGES.includes(value as Range) ? (value as Range) : fallback;
}

const DEFAULT_METRICS = ["temperature", "humidity", "pressure"];

const METRIC_DEFAULTS: Record<string, { max: number; label: string }> = {
  temperature: { max: 100, label: "Temp" },
  humidity: { max: 100, label: "Humidity" },
  pressure: { max: 1100, label: "Pressure" },
  vibration: { max: 100, label: "Vibration" },
  power: { max: 1000, label: "Power" },
  flow: { max: 100, label: "Flow" },
  level: { max: 100, label: "Level" },
  uptime_pct: { max: 100, label: "Uptime" },
  device_count: { max: 100, label: "Devices" },
  alert_count: { max: 50, label: "Alerts" },
};

export default function RadarRenderer({ config }: WidgetRendererProps) {
  const metrics =
    Array.isArray(config.radar_metrics) && (config.radar_metrics as unknown[]).length >= 3
      ? (config.radar_metrics as string[])
      : DEFAULT_METRICS;
  const range = asRange(config.time_range, "24h");
  const showLegend = (config.show_legend as boolean | undefined) ?? true;
  const isDark = useUIStore((s) => s.resolvedTheme === "dark");

  const queries = useQueries({
    queries: metrics.map((metric) => ({
      queryKey: ["widget-radar", metric, range],
      queryFn: () =>
        runAnalyticsQuery({
          metric,
          aggregation: "avg",
          time_range: range,
          group_by: null,
        }),
      refetchInterval: 60000,
    })),
  });

  const isLoading = queries.some((q) => q.isLoading);

  const option = useMemo<EChartsOption>(() => {
    const indicator = metrics.map((m) => {
      const def = METRIC_DEFAULTS[m];
      return {
        name: def?.label ?? m.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        max: def?.max ?? 100,
      };
    });

    const values = queries.map((q) => {
      const response = q.data as AnalyticsQueryResponse | undefined;
      return response?.summary?.avg ?? 0;
    });

    return {
      tooltip: { trigger: "item" },
      legend: showLegend
        ? {
            bottom: 0,
            textStyle: { color: isDark ? "#a1a1aa" : "#52525b", fontSize: 11 },
          }
        : { show: false },
      radar: {
        indicator,
        shape: "polygon",
        splitNumber: 4,
        axisName: { color: isDark ? "#a1a1aa" : "#52525b", fontSize: 11 },
        splitArea: {
          areaStyle: {
            color: isDark
              ? ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.05)"]
              : ["rgba(0,0,0,0.02)", "rgba(0,0,0,0.05)"],
          },
        },
        splitLine: {
          lineStyle: { color: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)" },
        },
        axisLine: {
          lineStyle: { color: isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)" },
        },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: values,
              name: "Current",
              symbol: "circle",
              symbolSize: 6,
              lineStyle: { width: 2, color: CHART_COLORS[0] },
              areaStyle: { color: CHART_COLORS[0], opacity: 0.15 },
              itemStyle: { color: CHART_COLORS[0] },
            },
          ],
        },
      ],
    };
  }, [queries, metrics, showLegend, isDark]);

  if (isLoading) return <Skeleton className="h-full w-full min-h-[120px]" />;

  return (
    <div className="h-full w-full min-h-[120px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}


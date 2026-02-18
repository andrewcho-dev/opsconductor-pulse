import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetHealth, getFleetUptimeSummary } from "@/services/api/devices";
import type { WidgetRendererProps } from "../widget-registry";

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export default function GaugeRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "uptime_pct";
  const min = asNumber(config.min, 0);
  const max = asNumber(config.max, 100);
  const decimalPrecision = (config.decimal_precision as number | undefined) ?? 1;
  const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];

  const needsUptime = metric === "uptime_pct";
  const needsHealth = metric === "health_score";

  const { data: uptimeData, isLoading: uptimeLoading } = useQuery({
    queryKey: ["widget-gauge", "uptime"],
    queryFn: getFleetUptimeSummary,
    enabled: needsUptime,
    refetchInterval: 30000,
  });

  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ["widget-gauge", "health"],
    queryFn: fetchFleetHealth,
    enabled: needsHealth,
    refetchInterval: 30000,
  });

  const value = needsUptime
    ? uptimeData?.avg_uptime_pct ?? 0
    : needsHealth
      ? healthData?.score ?? 0
      : 0;

  const isLoading = uptimeLoading || healthLoading;

  const option = useMemo<EChartsOption>(
    () => {
      const span = Math.max(1e-9, max - min);
      const sortedThresholds = [...thresholds].sort((a, b) => a.value - b.value);
      const axisLineColors: [number, string][] =
        sortedThresholds.length > 0
          ? [
              ...sortedThresholds.map((t) => {
                const stop = Math.min(1, Math.max(0, (t.value - min) / span));
                return [stop, t.color] as [number, string];
              }),
              [1, "#22c55e"], // remaining segment = healthy/green
            ]
          : [];

      return {
        series: [
          {
            type: "gauge",
            min,
            max,
            progress: { show: true, width: 10 },
            axisLine: {
              lineStyle: {
                width: 10,
                ...(axisLineColors.length > 0 ? { color: axisLineColors } : {}),
              },
            },
            axisTick: { show: false },
            splitLine: { length: 8 },
            axisLabel: { distance: 12, fontSize: 10 },
            pointer: { show: false },
            detail: {
              valueAnimation: true,
              formatter: (v: number) => `${Number(v).toFixed(decimalPrecision)}%`,
              fontSize: 18,
            },
            data: [{ value }],
          },
        ],
      };
    },
    [decimalPrecision, min, max, thresholds, value]
  );

  if (isLoading) return <Skeleton className="h-full w-full min-h-[100px]" />;

  return (
    <div className="h-full w-full min-h-[100px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}


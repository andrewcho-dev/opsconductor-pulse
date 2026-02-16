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
    () => ({
      series: [
        {
          type: "gauge",
          min,
          max,
          progress: { show: true, width: 10 },
          axisLine: { lineStyle: { width: 10 } },
          axisTick: { show: false },
          splitLine: { length: 8 },
          axisLabel: { distance: 12, fontSize: 10 },
          pointer: { show: false },
          detail: {
            valueAnimation: true,
            formatter: (v: number) => `${Number(v).toFixed(1)}%`,
            fontSize: 18,
          },
          data: [{ value }],
        },
      ],
    }),
    [min, max, value]
  );

  if (isLoading) return <Skeleton className="h-[220px] w-full" />;

  return <EChartWrapper option={option} style={{ height: 220 }} />;
}


import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchTelemetryHistory, type TelemetryHistoryResponse } from "@/services/api/devices";
import type { WidgetRendererProps } from "../widget-registry";

const VALID_RANGES = ["1h", "6h", "24h", "7d", "30d"] as const;
type Range = (typeof VALID_RANGES)[number];

function asRange(value: unknown, fallback: Range): Range {
  return VALID_RANGES.includes(value as Range) ? (value as Range) : fallback;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((x): x is string => typeof x === "string" && x.length > 0);
}

export default function LineChartRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "temperature";
  const range = asRange(config.time_range, "24h");
  const devices = asStringArray(config.devices);
  const deviceId = devices[0];

  const { data, isLoading } = useQuery({
    queryKey: ["widget-line-chart", deviceId, metric, range],
    queryFn: () => fetchTelemetryHistory(deviceId, metric, range),
    enabled: !!deviceId,
    refetchInterval: 30000,
  });

  const option = useMemo<EChartsOption>(() => {
    const points = (data as TelemetryHistoryResponse | undefined)?.points ?? [];
    const x = points.map((p) => p.time);
    const y = points.map((p) => p.avg ?? p.max ?? p.min ?? null);
    return {
      tooltip: { trigger: "axis" },
      grid: { left: 30, right: 10, top: 10, bottom: 30 },
      xAxis: { type: "category", data: x, axisLabel: { hideOverlap: true } },
      yAxis: { type: "value", scale: true },
      series: [
        {
          type: "line",
          data: y,
          showSymbol: false,
          smooth: true,
        },
      ],
    };
  }, [data]);

  if (!deviceId) {
    return (
      <div className="text-sm text-muted-foreground flex items-center justify-center h-full min-h-[140px]">
        No devices selected
      </div>
    );
  }

  if (isLoading) return <Skeleton className="h-[240px] w-full" />;

  return <EChartWrapper option={option} style={{ height: 240 }} />;
}


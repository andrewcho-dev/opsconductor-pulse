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

  const showLegend = (config.show_legend as boolean | undefined) ?? true;
  const showXAxis = (config.show_x_axis as boolean | undefined) ?? true;
  const showYAxis = (config.show_y_axis as boolean | undefined) ?? true;
  const yAxisMin = config.y_axis_min as number | undefined;
  const yAxisMax = config.y_axis_max as number | undefined;
  const thresholds =
    (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];

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
      legend: showLegend ? {} : { show: false },
      grid: {
        left: showYAxis ? 30 : 10,
        right: 10,
        top: 10,
        bottom: showXAxis ? 30 : 10,
      },
      xAxis: {
        type: "category",
        data: x,
        axisLabel: { hideOverlap: true, show: showXAxis },
        axisTick: { show: showXAxis },
        axisLine: { show: showXAxis },
      },
      yAxis: {
        type: "value",
        scale: true,
        min: yAxisMin,
        max: yAxisMax,
        axisLabel: { show: showYAxis },
        axisTick: { show: showYAxis },
        axisLine: { show: showYAxis },
        splitLine: { show: showYAxis },
      },
      series: [
        {
          type: "line",
          data: y,
          showSymbol: false,
          smooth: true,
          markLine:
            thresholds.length > 0
              ? {
                  silent: true,
                  symbol: "none",
                  data: thresholds.map((t) => ({
                    yAxis: t.value,
                    lineStyle: { color: t.color, type: "dashed", width: 1 },
                    label: {
                      show: !!t.label,
                      formatter: t.label || "",
                      position: "insideEndTop",
                      fontSize: 10,
                      color: t.color,
                    },
                  })),
                }
              : undefined,
        },
      ],
    };
  }, [data, showLegend, showXAxis, showYAxis, thresholds, yAxisMin, yAxisMax]);

  if (!deviceId) {
    return (
      <div className="text-sm text-muted-foreground flex items-center justify-center h-full min-h-[140px]">
        No devices selected
      </div>
    );
  }

  if (isLoading) return <Skeleton className="h-full w-full min-h-[120px]" />;

  return (
    <div className="h-full w-full min-h-[120px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}


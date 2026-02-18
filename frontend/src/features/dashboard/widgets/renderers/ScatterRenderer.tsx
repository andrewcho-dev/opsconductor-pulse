import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { runAnalyticsQuery, type AnalyticsQueryResponse } from "@/services/api/analytics";
import { CHART_COLORS } from "@/lib/charts/colors";
import type { WidgetRendererProps } from "../widget-registry";

const VALID_RANGES = ["1h", "6h", "24h", "7d", "30d"] as const;
type Range = (typeof VALID_RANGES)[number];

function asRange(value: unknown, fallback: Range): Range {
  return VALID_RANGES.includes(value as Range) ? (value as Range) : fallback;
}

export default function ScatterRenderer({ config }: WidgetRendererProps) {
  const xMetric = typeof config.x_metric === "string" ? config.x_metric : "temperature";
  const yMetric = typeof config.y_metric === "string" ? config.y_metric : "humidity";
  const range = asRange(config.time_range, "24h");

  const showLegend = (config.show_legend as boolean | undefined) ?? false;
  const showXAxis = (config.show_x_axis as boolean | undefined) ?? true;
  const showYAxis = (config.show_y_axis as boolean | undefined) ?? true;
  const thresholds =
    (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];

  const { data: xData, isLoading: xLoading } = useQuery({
    queryKey: ["widget-scatter-x", xMetric, range],
    queryFn: () =>
      runAnalyticsQuery({
        metric: xMetric,
        aggregation: "avg",
        time_range: range,
        group_by: "device",
      }),
    refetchInterval: 60000,
  });

  const { data: yData, isLoading: yLoading } = useQuery({
    queryKey: ["widget-scatter-y", yMetric, range],
    queryFn: () =>
      runAnalyticsQuery({
        metric: yMetric,
        aggregation: "avg",
        time_range: range,
        group_by: "device",
      }),
    refetchInterval: 60000,
  });

  const isLoading = xLoading || yLoading;

  const option = useMemo<EChartsOption>(() => {
    const xResponse = xData as AnalyticsQueryResponse | undefined;
    const yResponse = yData as AnalyticsQueryResponse | undefined;
    const xSeries = xResponse?.series ?? [];
    const ySeries = yResponse?.series ?? [];

    const xMap = new Map<string, number>();
    xSeries.forEach((s) => {
      const vals = s.points.filter((p) => p.value != null).map((p) => p.value!);
      if (vals.length > 0) {
        xMap.set(s.label, vals.reduce((a, b) => a + b, 0) / vals.length);
      }
    });

    const yMap = new Map<string, number>();
    ySeries.forEach((s) => {
      const vals = s.points.filter((p) => p.value != null).map((p) => p.value!);
      if (vals.length > 0) {
        yMap.set(s.label, vals.reduce((a, b) => a + b, 0) / vals.length);
      }
    });

    const scatterData: Array<[number, number, string]> = [];
    xMap.forEach((xVal, device) => {
      const yVal = yMap.get(device);
      if (yVal != null) {
        scatterData.push([xVal, yVal, device]);
      }
    });

    const formatLabel = (name: string) =>
      name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

    return {
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const p = params as { data: [number, number, string] };
          return `<strong>${p.data[2]}</strong><br/>${formatLabel(xMetric)}: ${p.data[0].toFixed(2)}<br/>${formatLabel(yMetric)}: ${p.data[1].toFixed(2)}`;
        },
      },
      legend: showLegend ? {} : { show: false },
      grid: {
        left: showYAxis ? 40 : 10,
        right: 15,
        top: 15,
        bottom: showXAxis ? 35 : 10,
      },
      xAxis: {
        type: "value",
        name: formatLabel(xMetric),
        nameLocation: "center",
        nameGap: 22,
        nameTextStyle: { fontSize: 11 },
        axisLabel: { show: showXAxis, fontSize: 10 },
        axisTick: { show: showXAxis },
        axisLine: { show: showXAxis },
        splitLine: { show: true, lineStyle: { type: "dashed", opacity: 0.3 } },
      },
      yAxis: {
        type: "value",
        name: formatLabel(yMetric),
        nameLocation: "center",
        nameGap: 30,
        nameTextStyle: { fontSize: 11 },
        axisLabel: { show: showYAxis, fontSize: 10 },
        axisTick: { show: showYAxis },
        axisLine: { show: showYAxis },
        splitLine: { show: true, lineStyle: { type: "dashed", opacity: 0.3 } },
      },
      series: [
        {
          type: "scatter",
          symbolSize: 12,
          data: scatterData,
          itemStyle: { color: CHART_COLORS[0], opacity: 0.8 },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.3)", borderWidth: 2 },
          },
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
  }, [xData, yData, xMetric, yMetric, showLegend, showXAxis, showYAxis, thresholds]);

  if (isLoading) return <Skeleton className="h-full w-full min-h-[120px]" />;

  return (
    <div className="h-full w-full min-h-[120px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}


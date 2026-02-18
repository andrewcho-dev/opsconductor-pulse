import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetSummary } from "@/services/api/devices";
import type { WidgetRendererProps } from "../widget-registry";

export default function BarChartRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "device_count";

  const showLegend = (config.show_legend as boolean | undefined) ?? true;
  const showXAxis = (config.show_x_axis as boolean | undefined) ?? true;
  const showYAxis = (config.show_y_axis as boolean | undefined) ?? true;
  const yAxisMin = config.y_axis_min as number | undefined;
  const yAxisMax = config.y_axis_max as number | undefined;
  const thresholds =
    (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];

  const { data, isLoading } = useQuery({
    queryKey: ["widget-bar-chart", metric],
    queryFn: fetchFleetSummary,
    refetchInterval: 30000,
  });

  const option = useMemo<EChartsOption>(() => {
    const online = data?.online ?? data?.ONLINE ?? 0;
    const stale = data?.STALE ?? 0;
    const offline = data?.offline ?? data?.OFFLINE ?? 0;
    const categories = ["Online", "Stale", "Offline"];
    const values = [online, stale, offline];
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
        data: categories,
        axisLabel: { show: showXAxis },
        axisTick: { show: showXAxis },
        axisLine: { show: showXAxis },
      },
      yAxis: {
        type: "value",
        min: yAxisMin,
        max: yAxisMax,
        axisLabel: { show: showYAxis },
        axisTick: { show: showYAxis },
        axisLine: { show: showYAxis },
        splitLine: { show: showYAxis },
      },
      series: [
        {
          type: "bar",
          data: values,
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

  if (isLoading) return <Skeleton className="h-full w-full min-h-[120px]" />;
  return (
    <div className="h-full w-full min-h-[120px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}


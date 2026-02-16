import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetSummary } from "@/services/api/devices";
import type { WidgetRendererProps } from "../widget-registry";

export default function BarChartRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "device_count";

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
      grid: { left: 30, right: 10, top: 10, bottom: 30 },
      xAxis: { type: "category", data: categories },
      yAxis: { type: "value" },
      series: [
        {
          type: "bar",
          data: values,
        },
      ],
    };
  }, [data]);

  if (isLoading) return <Skeleton className="h-[240px] w-full" />;
  return <EChartWrapper option={option} style={{ height: 240 }} />;
}


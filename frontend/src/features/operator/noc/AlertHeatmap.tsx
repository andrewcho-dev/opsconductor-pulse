import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchOperatorAlerts } from "@/services/api/operator";

interface AlertHeatmapProps {
  refreshInterval: number;
  isPaused: boolean;
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function AlertHeatmap({ refreshInterval, isPaused }: AlertHeatmapProps) {
  const { data } = useQuery({
    queryKey: ["noc-alert-heatmap"],
    queryFn: () => fetchOperatorAlerts("ALL", undefined, 200),
    refetchInterval: isPaused ? false : Math.max(refreshInterval, 60000),
  });

  const alerts = data?.alerts ?? [];

  const heatmapData = useMemo(() => {
    const counts: Record<string, number> = {};
    const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    alerts.forEach((alert) => {
      const date = new Date(alert.created_at);
      const millis = date.getTime();
      if (Number.isNaN(millis) || millis < sevenDaysAgo) return;
      const day = date.getDay();
      const hour = date.getHours();
      const key = `${day}-${hour}`;
      counts[key] = (counts[key] || 0) + 1;
    });
    return Array.from({ length: 7 }, (_, day) =>
      Array.from({ length: 24 }, (_, hour) => [hour, day, counts[`${day}-${hour}`] || 0] as [number, number, number])
    ).flat();
  }, [alerts]);

  const maxValue = useMemo(
    () => Math.max(1, ...heatmapData.map((point) => point[2])),
    [heatmapData]
  );

  const heatmapOption: echarts.EChartsOption = {
    backgroundColor: "transparent",
    tooltip: {
      position: "top",
      formatter: (p) => {
        const tuple = (Array.isArray(p) ? p[0]?.data : p.data) as [number, number, number] | undefined;
        if (!tuple) return "No data";
        return `${DAYS[tuple[1]]} ${tuple[0]}:00 - ${tuple[2]} alerts`;
      },
    },
    grid: { left: 60, right: 20, top: 30, bottom: 52 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      axisLabel: { color: "#9ca3af", fontSize: 9, interval: 2 },
      splitArea: { show: false },
    },
    yAxis: {
      type: "category",
      data: DAYS,
      axisLabel: { color: "#9ca3af", fontSize: 10 },
      splitArea: { show: false },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: {
        color: ["#1f2937", "#1e3a5f", "#1d4ed8", "#3b82f6", "#ef4444"],
      },
      textStyle: { color: "#9ca3af", fontSize: 9 },
    },
    series: [
      {
        type: "heatmap",
        data: heatmapData,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
      },
    ],
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium text-gray-300">Alert Volume - Last 7 Days (by hour)</div>
        <div className="text-xs text-gray-500">{alerts.length} alerts in last 7 days</div>
      </div>
      <EChartWrapper option={heatmapOption} style={{ height: 208 }} />
    </div>
  );
}

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchOperatorAlerts } from "@/services/api/operator";
import { NOC_THEME_NAME } from "@/lib/charts/nocTheme";
import { NOC_COLORS } from "./nocColors";

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
      axisLabel: { color: NOC_COLORS.textSecondary, fontSize: 9, interval: 2 },
      splitArea: { show: false },
    },
    yAxis: {
      type: "category",
      data: DAYS,
      axisLabel: { color: NOC_COLORS.textSecondary, fontSize: 10 },
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
        color: [
          NOC_COLORS.bg.cardBorder,
          NOC_COLORS.heatmapLow,
          NOC_COLORS.heatmapMid,
          NOC_COLORS.info,
          NOC_COLORS.critical,
        ],
      },
      textStyle: { color: NOC_COLORS.textSecondary, fontSize: 9 },
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
    <div
      className="rounded-lg border p-3"
      style={{ borderColor: NOC_COLORS.bg.cardBorder, backgroundColor: NOC_COLORS.bg.card }}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium" style={{ color: NOC_COLORS.textSecondary }}>
          Alert Volume - Last 7 Days (by hour)
        </div>
        <div className="text-xs" style={{ color: NOC_COLORS.neutral }}>
          {alerts.length} alerts in last 7 days
        </div>
      </div>
      <EChartWrapper option={heatmapOption} theme={NOC_THEME_NAME} style={{ height: 208 }} />
    </div>
  );
}

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchSystemMetricsHistory } from "@/services/api/operator";

interface MetricsChartGridProps {
  refreshInterval: number;
  isPaused: boolean;
}

function toSeriesPoints(points: Array<{ time: string; value: number }> | undefined): [number, number][] {
  if (!points) return [];
  return points.map((p) => [new Date(p.time).getTime(), p.value]);
}

function lineOption(
  data: [number, number][],
  color: string,
  yName: string,
  stepped = false,
  markAt?: number
): echarts.EChartsOption {
  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) =>
        typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value),
    },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: { type: "time", axisLabel: { color: "#9ca3af", fontSize: 10 } },
    yAxis: {
      type: "value",
      name: yName,
      nameTextStyle: { color: "#9ca3af", fontSize: 10 },
      axisLabel: { color: "#9ca3af", fontSize: 10 },
      splitLine: { lineStyle: { color: "#374151" } },
    },
    series: [
      {
        type: "line",
        smooth: !stepped,
        step: stepped ? "end" : undefined,
        data,
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        areaStyle: { color, opacity: 0.15 },
        showSymbol: false,
        markLine: markAt
          ? {
              symbol: ["none", "none"],
              lineStyle: { color: "#6b7280", type: "dashed" },
              data: [{ yAxis: markAt }],
            }
          : undefined,
      },
    ],
  };
}

function ChartCard({ title, option }: { title: string; option: echarts.EChartsOption }) {
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-3">
      <div className="mb-2 text-sm font-medium text-gray-200">{title}</div>
      <EChartWrapper option={option} style={{ height: 208 }} />
    </div>
  );
}

export function MetricsChartGrid({ refreshInterval, isPaused }: MetricsChartGridProps) {
  const queryRefetchInterval: number | false = isPaused
    ? false
    : Math.max(refreshInterval, 30000);

  const { data: ingest } = useQuery({
    queryKey: ["noc-chart-ingest"],
    queryFn: () =>
      fetchSystemMetricsHistory({
        metric: "messages_written",
        minutes: 60,
        service: "ingest",
        rate: true,
      }),
    refetchInterval: queryRefetchInterval,
  });

  const { data: alerts } = useQuery({
    queryKey: ["noc-chart-alerts"],
    queryFn: () =>
      fetchSystemMetricsHistory({
        metric: "alerts_open",
        minutes: 60,
        rate: true,
      }),
    refetchInterval: queryRefetchInterval,
  });

  const { data: queue } = useQuery({
    queryKey: ["noc-chart-queue-depth"],
    queryFn: () =>
      fetchSystemMetricsHistory({
        metric: "queue_depth",
        minutes: 60,
      }),
    refetchInterval: queryRefetchInterval,
  });

  const { data: dbConnections } = useQuery({
    queryKey: ["noc-chart-db-connections"],
    queryFn: () =>
      fetchSystemMetricsHistory({
        metric: "connections",
        minutes: 60,
      }),
    refetchInterval: queryRefetchInterval,
  });

  const ingestOption = useMemo(
    () => lineOption(toSeriesPoints(ingest?.points), "#3b82f6", "msg/s"),
    [ingest?.points]
  );
  const alertsOption = useMemo(
    () => lineOption(toSeriesPoints(alerts?.points), "#ef4444", "alerts/min"),
    [alerts?.points]
  );
  const queueOption = useMemo(
    () => lineOption(toSeriesPoints(queue?.points), "#f59e0b", "jobs", true, 1000),
    [queue?.points]
  );
  const dbConnOption = useMemo(
    () => lineOption(toSeriesPoints(dbConnections?.points), "#8b5cf6", "connections"),
    [dbConnections?.points]
  );

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <ChartCard title="Message Ingestion Rate" option={ingestOption} />
      <ChartCard title="Alert Fire Rate" option={alertsOption} />
      <ChartCard title="Worker Queue Depth" option={queueOption} />
      <ChartCard title="Database Connections" option={dbConnOption} />
    </div>
  );
}

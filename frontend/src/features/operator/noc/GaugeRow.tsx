import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchSystemAggregates, fetchSystemCapacity } from "@/services/api/system";
import { fetchSystemMetricsLatest } from "@/services/api/operator";
import { NOC_COLORS } from "./nocColors";

interface GaugeRowProps {
  refreshInterval: number;
  isPaused: boolean;
}

function getNestedNumber(obj: unknown, paths: string[]): number {
  if (!obj || typeof obj !== "object") return 0;
  for (const path of paths) {
    const keys = path.split(".");
    let current: unknown = obj;
    for (const key of keys) {
      if (!current || typeof current !== "object") {
        current = undefined;
        break;
      }
      current = (current as Record<string, unknown>)[key];
    }
    if (typeof current === "number" && Number.isFinite(current)) {
      return current;
    }
  }
  return 0;
}

function gaugeOption(
  value: number,
  max: number,
  colors: [number, string][],
  title: string,
  unit: string
): echarts.EChartsOption {
  const display = unit === "%" ? value.toFixed(1) : Math.round(value).toString();
  return {
    backgroundColor: "transparent",
    series: [
      {
        type: "gauge",
        min: 0,
        max,
        radius: "85%",
        axisLine: {
          lineStyle: {
            width: 12,
            color: colors,
          },
        },
        pointer: { itemStyle: { color: "auto" }, length: "60%", width: 6 },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { color: "auto", width: 2 } },
        axisLabel: { color: NOC_COLORS.textSecondary, fontSize: 10, distance: 15 },
        detail: {
          valueAnimation: true,
          formatter: `${display}${unit}`,
          color: NOC_COLORS.textPrimary,
          fontSize: 22,
          fontWeight: "bold",
          offsetCenter: [0, "65%"],
        },
        title: { color: NOC_COLORS.textSecondary, fontSize: 11, offsetCenter: [0, "90%"] },
        data: [{ value, name: title }],
      },
    ],
  };
}

export function GaugeRow({ refreshInterval, isPaused }: GaugeRowProps) {
  const { data: aggregates } = useQuery({
    queryKey: ["noc-gauges-aggregates"],
    queryFn: fetchSystemAggregates,
    refetchInterval: isPaused ? false : refreshInterval,
  });
  const { data: latest } = useQuery({
    queryKey: ["noc-gauges-latest"],
    queryFn: fetchSystemMetricsLatest,
    refetchInterval: isPaused ? false : refreshInterval,
  });
  const { data: capacity } = useQuery({
    queryKey: ["noc-gauges-capacity"],
    queryFn: fetchSystemCapacity,
    refetchInterval: isPaused ? false : refreshInterval,
  });

  const fleetOnlinePct = useMemo(() => {
    const online = aggregates?.devices.online ?? 0;
    const total = Math.max(aggregates?.devices.registered ?? 0, 1);
    return (online / total) * 100;
  }, [aggregates]);

  const ingestRate = useMemo(() => {
    return getNestedNumber(latest, [
      "ingest.ingest_rate",
      "ingest.messages_written",
      "ingest.messages_written_rate",
    ]);
  }, [latest]);

  const openAlerts = aggregates?.alerts.open ?? 0;

  const dbConnPct = useMemo(() => {
    const used = capacity?.postgres.connections_used ?? 0;
    const max = Math.max(capacity?.postgres.connections_max ?? 1, 1);
    return (used / max) * 100;
  }, [capacity]);

  const cards = [
    {
      key: "fleet-online",
      option: gaugeOption(
        fleetOnlinePct,
        100,
        [
          [0.8, NOC_COLORS.critical],
          [0.95, NOC_COLORS.warning],
          [1, NOC_COLORS.healthy],
        ],
        "Fleet Online",
        "%"
      ),
    },
    {
      key: "ingest-rate",
      option: gaugeOption(
        ingestRate,
        Math.max(ingestRate * 1.5, 100),
        [[1, NOC_COLORS.info]],
        "Ingest Rate",
        ""
      ),
    },
    {
      key: "open-alerts",
      option: gaugeOption(
        openAlerts,
        Math.max(openAlerts * 2, 50),
        [
          [0.2, NOC_COLORS.healthy],
          [0.5, NOC_COLORS.warning],
          [1, NOC_COLORS.critical],
        ],
        "Open Alerts",
        ""
      ),
    },
    {
      key: "db-conn",
      option: gaugeOption(
        dbConnPct,
        100,
        [
          [0.7, NOC_COLORS.healthy],
          [0.9, NOC_COLORS.warning],
          [1, NOC_COLORS.critical],
        ],
        "DB Conn Usage",
        "%"
      ),
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.key}
          className="h-48 rounded-lg border p-2"
          style={{ borderColor: NOC_COLORS.bg.cardBorder, backgroundColor: NOC_COLORS.bg.card }}
        >
          <EChartWrapper option={card.option} style={{ height: "100%" }} />
        </div>
      ))}
    </div>
  );
}

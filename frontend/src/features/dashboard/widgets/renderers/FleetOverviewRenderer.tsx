import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { WidgetRendererProps } from "../widget-registry";
import type { EChartsOption } from "echarts";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetSummary, fetchFleetHealth } from "@/services/api/devices";
import { useUIStore } from "@/stores/ui-store";
import { Skeleton } from "@/components/ui/skeleton";

type DisplayMode = "count" | "donut" | "health";

export default function FleetOverviewRenderer({ config }: WidgetRendererProps) {
  const displayMode = (config.display_mode as DisplayMode) ?? "count";
  const decimalPrecision = (config.decimal_precision as number | undefined) ?? 0;

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 30000,
  });

  const online = summary?.online ?? summary?.ONLINE ?? 0;
  const stale = summary?.STALE ?? 0;
  const offline = summary?.offline ?? summary?.OFFLINE ?? 0;
  const total = (summary?.total ?? summary?.total_devices ?? online + stale + offline) as number;

  if (summaryLoading) {
    return <Skeleton className="h-full w-full min-h-[100px]" />;
  }

  if (displayMode === "count") {
    return (
      <CountView
        total={total}
        online={online}
        offline={offline}
        decimalPrecision={decimalPrecision}
      />
    );
  }

  if (displayMode === "donut") {
    return <DonutView total={total} online={online} stale={stale} />;
  }

  if (displayMode === "health") {
    return <HealthView config={config} decimalPrecision={decimalPrecision} />;
  }

  return (
    <CountView total={total} online={online} offline={offline} decimalPrecision={decimalPrecision} />
  );
}

function CountView({
  total,
  online,
  offline,
  decimalPrecision,
}: {
  total: number;
  online: number;
  offline: number;
  decimalPrecision: number;
}) {
  const fmt = (n: number) =>
    n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: decimalPrecision });

  return (
    <div className="h-full flex items-center justify-between px-2">
      <div>
        <div className="text-2xl font-semibold">{fmt(total)}</div>
        <div className="text-xs text-muted-foreground">Total Devices</div>
      </div>
      <div className="text-right space-y-0.5">
        <div className="text-xs">
          <span className="text-green-500 font-medium">{fmt(online)}</span> online
        </div>
        <div className="text-xs">
          <span className="text-red-500 font-medium">{fmt(offline)}</span> offline
        </div>
      </div>
    </div>
  );
}

function DonutView({ total, online, stale }: { total: number; online: number; stale: number }) {
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);
  const isDark = resolvedTheme === "dark";

  const option = useMemo<EChartsOption>(
    () => ({
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: {
        bottom: 0,
        textStyle: { color: isDark ? "#a1a1aa" : "#52525b" },
      },
      series: [
        {
          type: "pie",
          radius: ["50%", "70%"],
          center: ["50%", "45%"],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: isDark ? "#18181b" : "#e4e4e7",
            borderWidth: 2,
          },
          label: {
            show: true,
            position: "center",
            formatter: () => `${total}\nDevices`,
            fontSize: 16,
            fontWeight: "bold",
            color: isDark ? "#fafafa" : "#18181b",
            lineHeight: 22,
          },
          labelLine: { show: false },
          data: [
            { value: online, name: "Online", itemStyle: { color: isDark ? "#22c55e" : "#16a34a" } },
            { value: stale, name: "Stale", itemStyle: { color: isDark ? "#f97316" : "#ea580c" } },
          ],
        },
      ],
    }),
    [total, online, stale, isDark]
  );

  return (
    <div className="h-full w-full min-h-[100px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}

function HealthView({
  config,
  decimalPrecision,
}: {
  config: Record<string, unknown>;
  decimalPrecision: number;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: fetchFleetHealth,
    refetchInterval: 30000,
  });

  const score = data?.score ?? 0;
  const total = data?.total_devices ?? 0;
  const online = data?.online ?? 0;
  const critical = data?.critical_alerts ?? 0;
  const healthy = Math.max(0, online - critical);

  const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];
  const thresholdColor = useMemo(() => {
    if (thresholds.length === 0) return undefined;
    const sorted = [...thresholds].sort((a, b) => b.value - a.value);
    return sorted.find((t) => score >= t.value)?.color;
  }, [thresholds, score]);

  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const dashOffset = circumference - progress;

  if (isLoading) return <Skeleton className="h-full w-full min-h-[100px]" />;

  return (
    <div className="h-full flex items-center gap-4 px-2">
      <div className="relative shrink-0">
        <svg viewBox="0 0 120 120" className="h-full max-h-[120px] w-auto shrink-0 -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className="stroke-foreground/10"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            stroke={thresholdColor}
            className="stroke-status-online transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold">{score.toFixed(decimalPrecision)}%</span>
        </div>
      </div>

      <div className="flex flex-col gap-1 min-w-0 text-sm">
        <div>
          <span className="font-medium">{healthy}</span>
          <span className="text-muted-foreground">/{total} devices healthy</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {online} online, {critical} with critical alerts
        </div>
      </div>
    </div>
  );
}


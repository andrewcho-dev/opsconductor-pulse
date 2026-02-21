# Task 1: Gauge Style Expansion

## Context

The current GaugeRenderer only has ONE style — a progress arc without a pointer. IoT dashboards from ThingsBoard, Ubidots, and Datacake offer 4-6 gauge styles. ECharts `type: "gauge"` is extraordinarily configurable — all 4 styles below are just different config options on the same series type.

## Step 1: Modify GaugeRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/GaugeRenderer.tsx`

Replace the entire `option` useMemo with a style-aware version. Read `gauge_style` from config:

```tsx
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchFleetHealth, getFleetUptimeSummary } from "@/services/api/devices";
import type { WidgetRendererProps } from "../widget-registry";

type GaugeStyle = "arc" | "speedometer" | "ring" | "grade";

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export default function GaugeRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "uptime_pct";
  const min = asNumber(config.min, 0);
  const max = asNumber(config.max, 100);
  const decimalPrecision = (config.decimal_precision as number | undefined) ?? 1;
  const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];
  const gaugeStyle = (config.gauge_style as GaugeStyle) ?? "arc";

  const needsUptime = metric === "uptime_pct";
  const needsHealth = metric === "health_score";

  const { data: uptimeData, isLoading: uptimeLoading } = useQuery({
    queryKey: ["widget-gauge", "uptime"],
    queryFn: getFleetUptimeSummary,
    enabled: needsUptime,
    refetchInterval: 30000,
  });

  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ["widget-gauge", "health"],
    queryFn: fetchFleetHealth,
    enabled: needsHealth,
    refetchInterval: 30000,
  });

  const value = needsUptime
    ? uptimeData?.avg_uptime_pct ?? 0
    : needsHealth
      ? healthData?.score ?? 0
      : 0;

  const isLoading = uptimeLoading || healthLoading;

  const option = useMemo<EChartsOption>(() => {
    const span = Math.max(1e-9, max - min);

    // Build threshold color stops for axis line
    const sortedThresholds = [...thresholds].sort((a, b) => a.value - b.value);
    const axisLineColors: [number, string][] =
      sortedThresholds.length > 0
        ? [
            ...sortedThresholds.map((t) => {
              const stop = Math.min(1, Math.max(0, (t.value - min) / span));
              return [stop, t.color] as [number, string];
            }),
            [1, "#22c55e"],
          ]
        : [];

    const formatter = (v: number) => `${Number(v).toFixed(decimalPrecision)}%`;

    if (gaugeStyle === "speedometer") {
      return {
        series: [{
          type: "gauge",
          startAngle: 210,
          endAngle: -30,
          min,
          max,
          pointer: { show: true, length: "60%", width: 6, itemStyle: { color: "auto" } },
          progress: { show: false },
          axisLine: {
            lineStyle: {
              width: 15,
              ...(axisLineColors.length > 0 ? { color: axisLineColors } : {}),
            },
          },
          axisTick: { show: true, distance: -15, length: 4, lineStyle: { width: 1 } },
          splitLine: { show: true, distance: -15, length: 10, lineStyle: { width: 2 } },
          axisLabel: { distance: 20, fontSize: 10 },
          detail: {
            valueAnimation: true,
            formatter,
            fontSize: 18,
            offsetCenter: [0, "70%"],
          },
          data: [{ value }],
        }],
      };
    }

    if (gaugeStyle === "ring") {
      return {
        series: [{
          type: "gauge",
          startAngle: 90,
          endAngle: -270,
          min,
          max,
          pointer: { show: false },
          progress: {
            show: true,
            width: 14,
            roundCap: true,
            itemStyle: axisLineColors.length > 0
              ? { color: axisLineColors[axisLineColors.length - 1]?.[1] ?? "#3b82f6" }
              : { color: "#3b82f6" },
          },
          axisLine: { lineStyle: { width: 14, color: [[1, "#e5e7eb"]] } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          detail: {
            valueAnimation: true,
            formatter,
            fontSize: 22,
            fontWeight: "bold" as const,
            offsetCenter: [0, 0],
          },
          data: [{ value }],
        }],
      };
    }

    if (gaugeStyle === "grade") {
      // Grade gauge: segmented color bands for good/warning/danger
      const gradeColors: [number, string][] =
        axisLineColors.length > 0
          ? axisLineColors
          : [
              [0.33, "#22c55e"],
              [0.66, "#f59e0b"],
              [1, "#ef4444"],
            ];
      return {
        series: [{
          type: "gauge",
          startAngle: 210,
          endAngle: -30,
          min,
          max,
          pointer: { show: true, length: "50%", width: 4, itemStyle: { color: "#6b7280" } },
          progress: { show: false },
          axisLine: { lineStyle: { width: 20, color: gradeColors } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          detail: {
            valueAnimation: true,
            formatter,
            fontSize: 18,
            offsetCenter: [0, "65%"],
          },
          data: [{ value }],
        }],
      };
    }

    // Default: "arc" — current progress arc style
    return {
      series: [{
        type: "gauge",
        min,
        max,
        progress: { show: true, width: 10 },
        axisLine: {
          lineStyle: {
            width: 10,
            ...(axisLineColors.length > 0 ? { color: axisLineColors } : {}),
          },
        },
        axisTick: { show: false },
        splitLine: { length: 8 },
        axisLabel: { distance: 12, fontSize: 10 },
        pointer: { show: false },
        detail: {
          valueAnimation: true,
          formatter,
          fontSize: 18,
        },
        data: [{ value }],
      }],
    };
  }, [decimalPrecision, gaugeStyle, min, max, thresholds, value]);

  if (isLoading) return <Skeleton className="h-full w-full min-h-[100px]" />;

  return (
    <div className="h-full w-full min-h-[100px]">
      <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
```

## Key differences between styles

| Style | Pointer | Progress arc | Tick marks | Axis labels | Color bands |
|-------|---------|-------------|------------|-------------|-------------|
| arc | No | Yes (10px) | No | Yes | Via thresholds |
| speedometer | Yes (60%) | No | Yes | Yes (20px) | Via thresholds |
| ring | No | Yes (14px, roundCap) | No | No | Single color |
| grade | Yes (50%) | No | No | No | Always 3-segment |

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

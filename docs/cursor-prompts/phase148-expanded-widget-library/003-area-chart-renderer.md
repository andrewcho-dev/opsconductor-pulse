# Task 3: Area Chart Renderer

## Context

Area charts are the most common IoT time-series visualization — every major platform (AWS IoT, Azure, ThingsBoard, Grafana) offers them. In ECharts, an area chart is a line chart with `areaStyle` — but we create a dedicated renderer so it can be used as a standalone widget type with optimized defaults (gradient fill, stacked support).

## Step 1: Create AreaChartRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/AreaChartRenderer.tsx` (NEW)

```tsx
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { fetchTelemetryHistory, type TelemetryHistoryResponse } from "@/services/api/devices";
import { CHART_COLORS } from "@/lib/charts/colors";
import { useUIStore } from "@/stores/ui-store";
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

export default function AreaChartRenderer({ config }: WidgetRendererProps) {
  const metric = typeof config.metric === "string" ? config.metric : "temperature";
  const range = asRange(config.time_range, "24h");
  const devices = asStringArray(config.devices);
  const deviceId = devices[0];
  const isDark = useUIStore((s) => s.resolvedTheme === "dark");

  const showLegend = (config.show_legend as boolean | undefined) ?? true;
  const showXAxis = (config.show_x_axis as boolean | undefined) ?? true;
  const showYAxis = (config.show_y_axis as boolean | undefined) ?? true;
  const yAxisMin = config.y_axis_min as number | undefined;
  const yAxisMax = config.y_axis_max as number | undefined;
  const isStacked = (config.stacked as boolean | undefined) ?? false;
  const isSmooth = (config.smooth as boolean | undefined) ?? true;
  const thresholds =
    (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];

  const { data, isLoading } = useQuery({
    queryKey: ["widget-area-chart", deviceId, metric, range],
    queryFn: () => fetchTelemetryHistory(deviceId, metric, range),
    enabled: !!deviceId,
    refetchInterval: 30000,
  });

  const option = useMemo<EChartsOption>(() => {
    const points = (data as TelemetryHistoryResponse | undefined)?.points ?? [];
    const x = points.map((p) => p.time);
    const y = points.map((p) => p.avg ?? p.max ?? p.min ?? null);

    const seriesColor = CHART_COLORS[0];

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
        boundaryGap: false,
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
          smooth: isSmooth,
          ...(isStacked ? { stack: "total" } : {}),
          areaStyle: {
            opacity: 0.4,
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: seriesColor },
                { offset: 1, color: isDark ? "rgba(0,0,0,0)" : "rgba(255,255,255,0)" },
              ],
            },
          },
          lineStyle: { width: 2, color: seriesColor },
          itemStyle: { color: seriesColor },
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
  }, [data, isDark, isSmooth, isStacked, showLegend, showXAxis, showYAxis, thresholds, yAxisMin, yAxisMax]);

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
```

## Key differences from LineChartRenderer

1. `areaStyle` with linear gradient fill (top = series color → bottom = transparent)
2. `boundaryGap: false` on xAxis for edge-to-edge fill
3. `stacked` config option for stacked area support
4. Gradient direction is theme-aware (transparent fades to black in dark mode, white in light)

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

# Task 002: Chart Wrapper Components

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Task 1 installed ECharts and uPlot with theme/config/transforms. This task creates the React wrapper components that encapsulate chart lifecycle management (create, resize, update, dispose). These wrappers are used by the device detail page in Task 4.

**Read first**:
- `frontend/src/lib/charts/theme.ts` — `ECHARTS_THEME` constant
- `frontend/src/lib/charts/colors.ts` — `getSeriesColor()`, `GAUGE_COLORS`
- `frontend/src/lib/charts/metric-config.ts` — `getMetricConfig()`, `MetricConfig`
- `frontend/src/lib/charts/transforms.ts` — `toUPlotData()`, `TIME_RANGES`
- `frontend/src/components/shared/WidgetErrorBoundary.tsx` — error boundary pattern

---

## Task

### 2.1 Create ECharts React wrapper

**File**: `frontend/src/lib/charts/EChartWrapper.tsx` (NEW)

A generic wrapper that manages ECharts instance lifecycle. Handles init, resize, option updates, and dispose.

```tsx
import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { ECHARTS_THEME } from "./theme";
import { cn } from "@/lib/utils";

interface EChartWrapperProps {
  option: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  /** If true, merge new options instead of replacing */
  notMerge?: boolean;
}

export function EChartWrapper({
  option,
  className,
  style,
  notMerge = false,
}: EChartWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = echarts.init(containerRef.current, ECHARTS_THEME, {
      renderer: "canvas",
    });
    chartRef.current = chart;

    // ResizeObserver for responsive sizing
    const observer = new ResizeObserver(() => {
      chart.resize();
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  // Update options when they change
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.setOption(option, notMerge);
    }
  }, [option, notMerge]);

  return (
    <div
      ref={containerRef}
      className={cn("w-full", className)}
      style={{ height: 200, ...style }}
    />
  );
}
```

### 2.2 Create uPlot React wrapper

**File**: `frontend/src/lib/charts/UPlotChart.tsx` (NEW)

A wrapper for uPlot that manages instance lifecycle. uPlot is imperative — we create an instance with `new uPlot(opts, data, target)` and update it with `chart.setData(newData)`.

```tsx
import { useEffect, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { cn } from "@/lib/utils";

interface UPlotChartProps {
  options: Omit<uPlot.Options, "width" | "height">;
  data: uPlot.AlignedData;
  className?: string;
  height?: number;
}

export function UPlotChart({
  options,
  data,
  className,
  height = 200,
}: UPlotChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);

  // Create chart on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;

    const chart = new uPlot(
      { ...options, width, height },
      data,
      container
    );
    chartRef.current = chart;

    // ResizeObserver for responsive width
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && chartRef.current) {
        chartRef.current.setSize({
          width: entry.contentRect.width,
          height,
        });
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.destroy();
      chartRef.current = null;
    };
    // Re-create chart when options change (options define series, axes, etc.)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options, height]);

  // Update data without recreating the chart
  useEffect(() => {
    if (chartRef.current && data) {
      chartRef.current.setData(data);
    }
  }, [data]);

  return (
    <div
      ref={containerRef}
      className={cn("w-full", className)}
    />
  );
}
```

### 2.3 Create MetricGauge component

**File**: `frontend/src/lib/charts/MetricGauge.tsx` (NEW)

An ECharts gauge chart that displays a single metric's current value with color zones. Uses the metric configuration from `metric-config.ts`.

```tsx
import { useMemo, memo } from "react";
import { EChartWrapper } from "./EChartWrapper";
import { getMetricConfig } from "./metric-config";
import type { EChartsOption } from "echarts";

interface MetricGaugeProps {
  metricName: string;
  value: number | null;
  /** Optional data values for auto-scaling unknown metrics */
  allValues?: number[];
  className?: string;
}

function MetricGaugeInner({
  metricName,
  value,
  allValues,
  className,
}: MetricGaugeProps) {
  const config = useMemo(
    () => getMetricConfig(metricName, allValues),
    [metricName, allValues]
  );

  const option = useMemo<EChartsOption>(() => {
    // Build color stops for the gauge arc from zones
    const axisLineColors: [number, string][] = config.zones.map((z) => {
      const stop = (z.max - config.min) / (config.max - config.min);
      return [Math.min(1, Math.max(0, stop)), z.color];
    });

    return {
      series: [
        {
          type: "gauge",
          startAngle: 210,
          endAngle: -30,
          min: config.min,
          max: config.max,
          radius: "90%",
          progress: {
            show: true,
            width: 12,
          },
          axisLine: {
            lineStyle: {
              width: 12,
              color: axisLineColors,
            },
          },
          axisTick: { show: false },
          splitLine: {
            length: 8,
            lineStyle: { width: 1, color: "#52525b" },
          },
          axisLabel: {
            distance: 16,
            fontSize: 10,
            color: "#71717a",
            formatter: (v: number) => {
              if (v === config.min || v === config.max) {
                return `${v}`;
              }
              return "";
            },
          },
          pointer: {
            length: "55%",
            width: 4,
            itemStyle: { color: "auto" },
          },
          anchor: {
            show: true,
            size: 8,
            itemStyle: {
              borderWidth: 2,
              borderColor: "#52525b",
            },
          },
          title: {
            offsetCenter: [0, "70%"],
            fontSize: 12,
            color: "#a1a1aa",
          },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, "45%"],
            fontSize: 20,
            fontWeight: "bold",
            color: "#fafafa",
            formatter: (v: number) => {
              if (v == null) return "—";
              return `${v.toFixed(config.precision)}${config.unit}`;
            },
          },
          data: [
            {
              value: value ?? 0,
              name: config.label,
            },
          ],
        },
      ],
    };
  }, [value, config]);

  return (
    <EChartWrapper
      option={option}
      className={className}
      style={{ height: 180 }}
    />
  );
}

export const MetricGauge = memo(MetricGaugeInner);
```

### 2.4 Create TimeSeriesChart component

**File**: `frontend/src/lib/charts/TimeSeriesChart.tsx` (NEW)

A uPlot-based line chart for displaying a single metric's historical values. Handles dark theme styling, axis formatting, and cursor crosshair.

```tsx
import { useMemo, memo } from "react";
import type uPlot from "uplot";
import { UPlotChart } from "./UPlotChart";
import { toUPlotData } from "./transforms";
import { getMetricConfig } from "./metric-config";
import { getSeriesColor } from "./colors";
import type { TelemetryPoint } from "@/services/api/types";

interface TimeSeriesChartProps {
  metricName: string;
  points: TelemetryPoint[];
  colorIndex?: number;
  height?: number;
  className?: string;
}

function TimeSeriesChartInner({
  metricName,
  points,
  colorIndex = 0,
  height = 200,
  className,
}: TimeSeriesChartProps) {
  const config = useMemo(
    () => getMetricConfig(metricName),
    [metricName]
  );

  const data = useMemo(
    () => toUPlotData(points, metricName) as uPlot.AlignedData,
    [points, metricName]
  );

  const options = useMemo<Omit<uPlot.Options, "width" | "height">>(
    () => ({
      scales: {
        x: { time: true },
        y: {},
      },
      axes: [
        {
          // X-axis (time)
          stroke: "#71717a",
          grid: { stroke: "#27272a", width: 1 },
          ticks: { stroke: "#3f3f46", width: 1 },
        },
        {
          // Y-axis (values)
          stroke: "#71717a",
          grid: { stroke: "#27272a", width: 1 },
          ticks: { stroke: "#3f3f46", width: 1 },
          label: `${config.label}${config.unit ? ` (${config.unit})` : ""}`,
          labelSize: 16,
          labelFont: "11px system-ui",
          size: 60,
        },
      ],
      cursor: {
        drag: { x: false, y: false },
      },
      series: [
        {}, // timestamps series (always first, no config)
        {
          label: config.label,
          stroke: getSeriesColor(colorIndex),
          width: 2,
          points: { show: false },
          spanGaps: true,
        },
      ],
    }),
    [config, colorIndex]
  );

  if (data[0].length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-muted-foreground border border-border rounded-md"
        style={{ height }}
      >
        No data for {config.label}
      </div>
    );
  }

  return (
    <UPlotChart
      options={options}
      data={data}
      height={height}
      className={className}
    />
  );
}

export const TimeSeriesChart = memo(TimeSeriesChartInner);
```

### 2.5 Update module index

**File**: `frontend/src/lib/charts/index.ts` (MODIFY)

Add exports for the new chart components.

Add these lines at the end of the existing index.ts:

```typescript
// Chart components
export { EChartWrapper } from "./EChartWrapper";
export { UPlotChart } from "./UPlotChart";
export { MetricGauge } from "./MetricGauge";
export { TimeSeriesChart } from "./TimeSeriesChart";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/lib/charts/EChartWrapper.tsx` | Generic ECharts React wrapper |
| CREATE | `frontend/src/lib/charts/UPlotChart.tsx` | Generic uPlot React wrapper |
| CREATE | `frontend/src/lib/charts/MetricGauge.tsx` | Single metric gauge (ECharts) |
| CREATE | `frontend/src/lib/charts/TimeSeriesChart.tsx` | Time-series line chart (uPlot) |
| MODIFY | `frontend/src/lib/charts/index.ts` | Add component exports |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Verify files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/lib/charts/*.tsx
```

Should show: EChartWrapper.tsx, UPlotChart.tsx, MetricGauge.tsx, TimeSeriesChart.tsx

### Step 4: Verify implementation

Read the files and confirm:
- [ ] `EChartWrapper` creates echarts instance with `ECHARTS_THEME`
- [ ] `EChartWrapper` uses ResizeObserver for responsive sizing
- [ ] `EChartWrapper` disposes chart on unmount
- [ ] `EChartWrapper` updates options when props change
- [ ] `UPlotChart` creates uPlot instance with container width
- [ ] `UPlotChart` uses ResizeObserver for responsive width
- [ ] `UPlotChart` calls `setData()` when data prop changes
- [ ] `UPlotChart` destroys instance on unmount
- [ ] `MetricGauge` uses `getMetricConfig()` for ranges and zones
- [ ] `MetricGauge` builds gauge color stops from zones
- [ ] `MetricGauge` shows formatted value with unit
- [ ] `MetricGauge` wrapped in React.memo
- [ ] `TimeSeriesChart` calls `toUPlotData()` for data transformation
- [ ] `TimeSeriesChart` uses dark theme colors for axes and grid
- [ ] `TimeSeriesChart` shows empty state when no data
- [ ] `TimeSeriesChart` wrapped in React.memo

### Step 5: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `EChartWrapper` — generic ECharts wrapper with init/resize/update/dispose
- [ ] `UPlotChart` — generic uPlot wrapper with create/resize/setData/destroy
- [ ] `MetricGauge` — ECharts gauge showing metric value with colored zones
- [ ] `TimeSeriesChart` — uPlot line chart with dark theme styling
- [ ] All components use ResizeObserver for responsive sizing
- [ ] All components properly clean up on unmount
- [ ] All visualization components wrapped in React.memo
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Add chart wrapper components for ECharts and uPlot

EChartWrapper and UPlotChart handle lifecycle (init, resize,
update, dispose). MetricGauge renders ECharts gauge with color
zones. TimeSeriesChart renders uPlot line chart with dark theme.

Phase 20 Task 2: Chart Components
```

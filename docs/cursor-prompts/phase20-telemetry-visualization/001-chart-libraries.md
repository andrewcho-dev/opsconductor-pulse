# Task 001: Chart Library Installation + Configuration

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 19 added Zustand stores and WebSocket infrastructure. The `frontend/src/lib/charts/` directory exists but is empty — it was reserved for Phase 20. This task installs the chart libraries, creates the dark theme configuration, defines metric metadata, and builds data transformation utilities.

**Read first**:
- `frontend/package.json` — current dependencies (no chart libraries yet)
- `frontend/src/index.css` — existing dark theme CSS variables (HSL format)
- `frontend/src/services/api/types.ts` — TelemetryPoint type definition
- `docs/cursor-prompts/phase20-telemetry-visualization/INSTRUCTIONS.md` — architecture overview

---

## Task

### 1.1 Install chart libraries

```bash
cd /home/opsconductor/simcloud/frontend
npm install echarts uplot
```

Note: Both libraries ship with TypeScript declarations. No `@types/*` packages needed.

### 1.2 Install shadcn Tabs component

The device detail page needs a tabs component for the time range selector.

```bash
cd /home/opsconductor/simcloud/frontend
npx shadcn@latest add tabs
```

This creates `frontend/src/components/ui/tabs.tsx`.

### 1.3 Create chart color palette

**File**: `frontend/src/lib/charts/colors.ts` (NEW)

A consistent color palette for chart series. These colors work on dark backgrounds and are distinguishable for colorblind users.

```typescript
/**
 * Chart color palette — dark-theme optimized, colorblind-friendly.
 * Colors are ordered for maximum visual distinction.
 */
export const CHART_COLORS = [
  "#3b82f6", // blue-500
  "#22c55e", // green-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#a855f7", // purple-500
  "#06b6d4", // cyan-500
  "#f97316", // orange-500
  "#ec4899", // pink-500
] as const;

/** Get a color by index, cycling through the palette */
export function getSeriesColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

/** Gauge zone colors */
export const GAUGE_COLORS = {
  good: "#22c55e",    // green
  warning: "#f59e0b", // amber
  danger: "#ef4444",  // red
  neutral: "#6b7280", // gray
} as const;
```

### 1.4 Create metric configuration

**File**: `frontend/src/lib/charts/metric-config.ts` (NEW)

Defines known metric ranges, units, labels, and gauge color zones. Unknown metrics fall back to auto-scaling.

```typescript
export interface GaugeZone {
  min: number;
  max: number;
  color: string;
}

export interface MetricConfig {
  label: string;
  unit: string;
  min: number;
  max: number;
  precision: number;
  zones: GaugeZone[];
}

/**
 * Known metric configurations with sensible gauge ranges.
 * Any metric NOT in this map will be auto-scaled from the data.
 */
export const KNOWN_METRICS: Record<string, MetricConfig> = {
  battery_pct: {
    label: "Battery",
    unit: "%",
    min: 0,
    max: 100,
    precision: 1,
    zones: [
      { min: 0, max: 20, color: "#ef4444" },
      { min: 20, max: 50, color: "#f59e0b" },
      { min: 50, max: 100, color: "#22c55e" },
    ],
  },
  temp_c: {
    label: "Temperature",
    unit: "°C",
    min: -20,
    max: 80,
    precision: 1,
    zones: [
      { min: -20, max: 0, color: "#3b82f6" },
      { min: 0, max: 40, color: "#22c55e" },
      { min: 40, max: 60, color: "#f59e0b" },
      { min: 60, max: 80, color: "#ef4444" },
    ],
  },
  rssi_dbm: {
    label: "RSSI",
    unit: "dBm",
    min: -100,
    max: 0,
    precision: 0,
    zones: [
      { min: -100, max: -80, color: "#ef4444" },
      { min: -80, max: -60, color: "#f59e0b" },
      { min: -60, max: 0, color: "#22c55e" },
    ],
  },
  snr_db: {
    label: "SNR",
    unit: "dB",
    min: 0,
    max: 30,
    precision: 1,
    zones: [
      { min: 0, max: 10, color: "#ef4444" },
      { min: 10, max: 15, color: "#f59e0b" },
      { min: 15, max: 30, color: "#22c55e" },
    ],
  },
  humidity_pct: {
    label: "Humidity",
    unit: "%",
    min: 0,
    max: 100,
    precision: 1,
    zones: [
      { min: 0, max: 30, color: "#f59e0b" },
      { min: 30, max: 60, color: "#22c55e" },
      { min: 60, max: 80, color: "#f59e0b" },
      { min: 80, max: 100, color: "#ef4444" },
    ],
  },
  pressure_psi: {
    label: "Pressure",
    unit: "psi",
    min: 0,
    max: 200,
    precision: 1,
    zones: [
      { min: 0, max: 150, color: "#22c55e" },
      { min: 150, max: 180, color: "#f59e0b" },
      { min: 180, max: 200, color: "#ef4444" },
    ],
  },
  vibration_g: {
    label: "Vibration",
    unit: "g",
    min: 0,
    max: 10,
    precision: 2,
    zones: [
      { min: 0, max: 2, color: "#22c55e" },
      { min: 2, max: 5, color: "#f59e0b" },
      { min: 5, max: 10, color: "#ef4444" },
    ],
  },
};

/**
 * Get config for a metric. Returns known config or auto-generated config
 * based on the provided data range.
 */
export function getMetricConfig(
  metricName: string,
  values?: number[]
): MetricConfig {
  const known = KNOWN_METRICS[metricName];
  if (known) return known;

  // Auto-generate config from data range
  let min = 0;
  let max = 100;
  if (values && values.length > 0) {
    const dataMin = Math.min(...values);
    const dataMax = Math.max(...values);
    const range = dataMax - dataMin || 1;
    min = dataMin - range * 0.1;
    max = dataMax + range * 0.1;
  }

  return {
    label: metricName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    unit: "",
    min,
    max,
    precision: 2,
    zones: [{ min, max, color: "#3b82f6" }],
  };
}
```

### 1.5 Create data transformation utilities

**File**: `frontend/src/lib/charts/transforms.ts` (NEW)

Transforms the API's row-major `TelemetryPoint[]` into formats needed by uPlot (column-major) and ECharts.

```typescript
import type { TelemetryPoint } from "@/services/api/types";

/**
 * uPlot expects column-major data: [timestamps[], values[]].
 * Timestamps must be Unix seconds (not milliseconds).
 */
export function toUPlotData(
  points: TelemetryPoint[],
  metricName: string
): [number[], (number | null)[]] {
  const timestamps: number[] = [];
  const values: (number | null)[] = [];

  // Points come from API sorted DESC (newest first) — reverse for chronological
  for (let i = points.length - 1; i >= 0; i--) {
    const p = points[i];
    timestamps.push(new Date(p.timestamp).getTime() / 1000);
    const v = p.metrics[metricName];
    values.push(typeof v === "number" ? v : null);
  }

  return [timestamps, values];
}

/**
 * Extract all unique metric names from a set of telemetry points.
 * Only includes numeric metrics (filters out boolean values).
 */
export function discoverMetrics(points: TelemetryPoint[]): string[] {
  const metricSet = new Set<string>();
  for (const p of points) {
    for (const [key, value] of Object.entries(p.metrics)) {
      if (typeof value === "number") {
        metricSet.add(key);
      }
    }
  }
  // Sort: known metrics first (battery, temp, rssi, snr), then alphabetical
  const known = ["battery_pct", "temp_c", "rssi_dbm", "snr_db"];
  const sorted = [...metricSet].sort((a, b) => {
    const aIdx = known.indexOf(a);
    const bIdx = known.indexOf(b);
    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
    if (aIdx !== -1) return -1;
    if (bIdx !== -1) return 1;
    return a.localeCompare(b);
  });
  return sorted;
}

/**
 * Get the latest value for a metric from a telemetry array.
 * Points are typically sorted DESC from the API.
 */
export function getLatestValue(
  points: TelemetryPoint[],
  metricName: string
): number | null {
  for (const p of points) {
    const v = p.metrics[metricName];
    if (typeof v === "number") return v;
  }
  return null;
}

/**
 * Get all numeric values for a metric from a telemetry array.
 * Useful for computing auto-scale ranges.
 */
export function getMetricValues(
  points: TelemetryPoint[],
  metricName: string
): number[] {
  const values: number[] = [];
  for (const p of points) {
    const v = p.metrics[metricName];
    if (typeof v === "number") values.push(v);
  }
  return values;
}

/**
 * Compute a time range start timestamp for a given range string.
 * Returns ISO 8601 string.
 */
export function getTimeRangeStart(range: string): string {
  const now = new Date();
  switch (range) {
    case "1h":
      now.setHours(now.getHours() - 1);
      break;
    case "6h":
      now.setHours(now.getHours() - 6);
      break;
    case "24h":
      now.setHours(now.getHours() - 24);
      break;
    case "7d":
      now.setDate(now.getDate() - 7);
      break;
    default:
      now.setHours(now.getHours() - 1);
  }
  return now.toISOString();
}

/** Time range options for the UI */
export const TIME_RANGES = [
  { value: "1h", label: "1 Hour" },
  { value: "6h", label: "6 Hours" },
  { value: "24h", label: "24 Hours" },
  { value: "7d", label: "7 Days" },
] as const;

export type TimeRange = (typeof TIME_RANGES)[number]["value"];
```

### 1.6 Create ECharts dark theme

**File**: `frontend/src/lib/charts/theme.ts` (NEW)

Registers a custom ECharts theme that matches our Tailwind dark theme.

```typescript
import * as echarts from "echarts";
import { CHART_COLORS } from "./colors";

/** ECharts theme name — use this when initializing charts */
export const ECHARTS_THEME = "pulse-dark";

/**
 * Register the Pulse dark theme with ECharts.
 * Call this once at app startup.
 */
export function registerPulseDarkTheme(): void {
  echarts.registerTheme(ECHARTS_THEME, {
    color: [...CHART_COLORS],
    backgroundColor: "transparent",
    textStyle: {
      color: "#a1a1aa", // zinc-400
    },
    title: {
      textStyle: { color: "#fafafa" },
      subtextStyle: { color: "#a1a1aa" },
    },
    gauge: {
      axisLine: {
        lineStyle: {
          color: [[1, "#27272a"]], // zinc-800
        },
      },
      axisTick: { lineStyle: { color: "#52525b" } },
      splitLine: { lineStyle: { color: "#52525b" } },
      axisLabel: { color: "#a1a1aa" },
      detail: {
        color: "#fafafa",
      },
      title: {
        color: "#a1a1aa",
      },
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: "#3f3f46" } },
      axisTick: { lineStyle: { color: "#3f3f46" } },
      axisLabel: { color: "#a1a1aa" },
      splitLine: { lineStyle: { color: "#27272a" } },
    },
    valueAxis: {
      axisLine: { lineStyle: { color: "#3f3f46" } },
      axisTick: { lineStyle: { color: "#3f3f46" } },
      axisLabel: { color: "#a1a1aa" },
      splitLine: { lineStyle: { color: "#27272a" } },
    },
    legend: {
      textStyle: { color: "#a1a1aa" },
    },
    tooltip: {
      backgroundColor: "#18181b",
      borderColor: "#3f3f46",
      textStyle: { color: "#fafafa" },
    },
  });
}
```

### 1.7 Create module index

**File**: `frontend/src/lib/charts/index.ts` (NEW)

```typescript
// Configuration
export { CHART_COLORS, getSeriesColor, GAUGE_COLORS } from "./colors";
export {
  KNOWN_METRICS,
  getMetricConfig,
  type MetricConfig,
  type GaugeZone,
} from "./metric-config";

// Data transforms
export {
  toUPlotData,
  discoverMetrics,
  getLatestValue,
  getMetricValues,
  getTimeRangeStart,
  TIME_RANGES,
  type TimeRange,
} from "./transforms";

// ECharts theme
export { ECHARTS_THEME, registerPulseDarkTheme } from "./theme";
```

### 1.8 Register ECharts theme at app startup

**File**: `frontend/src/App.tsx` (MODIFY)

Add the theme registration call before the App component. This runs once when the module is loaded.

Add this import at the top of the file:

```typescript
import { registerPulseDarkTheme } from "@/lib/charts/theme";
```

Add the registration call before the App function:

```typescript
// Register ECharts dark theme (runs once on module load)
registerPulseDarkTheme();
```

Place it between the imports and the `function App()` declaration.

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/lib/charts/colors.ts` | Chart color palette |
| CREATE | `frontend/src/lib/charts/metric-config.ts` | Known metric ranges and units |
| CREATE | `frontend/src/lib/charts/transforms.ts` | Data transformation utilities |
| CREATE | `frontend/src/lib/charts/theme.ts` | ECharts dark theme registration |
| CREATE | `frontend/src/lib/charts/index.ts` | Module exports |
| MODIFY | `frontend/src/App.tsx` | Register ECharts theme on load |

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
ls /home/opsconductor/simcloud/frontend/src/lib/charts/
```

Should show: colors.ts, metric-config.ts, transforms.ts, theme.ts, index.ts

### Step 4: Verify chart packages installed

```bash
cd /home/opsconductor/simcloud/frontend && node -e "require('echarts'); console.log('echarts OK')"
cd /home/opsconductor/simcloud/frontend && node -e "require('uplot'); console.log('uplot OK')"
```

### Step 5: Verify tabs component

```bash
ls /home/opsconductor/simcloud/frontend/src/components/ui/tabs.tsx
```

### Step 6: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `echarts` and `uplot` installed as dependencies
- [ ] shadcn Tabs component added
- [ ] `CHART_COLORS` palette with 8 dark-theme optimized colors
- [ ] `KNOWN_METRICS` config for battery_pct, temp_c, rssi_dbm, snr_db, humidity_pct, pressure_psi, vibration_g
- [ ] `getMetricConfig()` returns known config or auto-generated fallback
- [ ] `toUPlotData()` converts TelemetryPoint[] to column-major [timestamps[], values[]]
- [ ] `discoverMetrics()` extracts unique metric names sorted with known metrics first
- [ ] `getTimeRangeStart()` computes ISO timestamps for 1h/6h/24h/7d ranges
- [ ] `TIME_RANGES` constant for UI
- [ ] ECharts dark theme registered matching Tailwind dark theme
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Install ECharts and uPlot with dark theme configuration

Chart color palette, known metric configs with gauge zones,
data transform utilities for uPlot column-major format.
ECharts dark theme registered at app startup.

Phase 20 Task 1: Chart Libraries
```

# Task 8: Wire Up Registry and Display Options

## Context

Tasks 1-7 created 5 new renderer files and modified 3 existing ones. Now we need to register everything in the widget system: new widget types in WIDGET_REGISTRY, expanded DISPLAY_OPTIONS for cross-type switching, new DISPLAY_RENDERERS entries, updated WidgetType union, and new icons in AddWidgetDrawer.

## Step 1: Update WidgetType in dashboards.ts

**File:** `frontend/src/services/api/dashboards.ts`

Add the 5 new widget types to the `WidgetType` union:

```typescript
export type WidgetType =
  | "kpi_tile"
  | "line_chart"
  | "bar_chart"
  | "gauge"
  | "table"
  | "alert_feed"
  | "fleet_overview"
  | "fleet_status"
  | "device_count"
  | "health_score"
  // Phase 148 additions:
  | "area_chart"
  | "stat_card"
  | "pie_chart"
  | "scatter"
  | "radar";
```

## Step 2: Add new widget types to WIDGET_REGISTRY

**File:** `frontend/src/features/dashboard/widgets/widget-registry.ts`

Add these 5 new entries to WIDGET_REGISTRY after the existing entries:

```typescript
  area_chart: {
    type: "area_chart",
    label: "Area Chart",
    description: "Filled area chart with gradient. Ideal for showing volume and trends over time. Supports stacking.",
    category: "charts",
    icon: "AreaChart",
    defaultTitle: "Area Trend",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 12, h: 6 },
    defaultConfig: { metric: "temperature", time_range: "24h", devices: [] },
    component: () => import("./renderers/AreaChartRenderer"),
  },
  stat_card: {
    type: "stat_card",
    label: "Stat Card",
    description: "Metric value with sparkline trend and directional arrow. At-a-glance monitoring with context.",
    category: "metrics",
    icon: "Activity",
    defaultTitle: "Metric",
    defaultSize: { w: 2, h: 1 },
    minSize: { w: 2, h: 1 },
    maxSize: { w: 4, h: 2 },
    defaultConfig: { metric: "device_count" },
    component: () => import("./renderers/StatCardRenderer"),
  },
  pie_chart: {
    type: "pie_chart",
    label: "Pie / Donut",
    description: "Proportional breakdown of fleet status, alert severity, or grouped metric data.",
    category: "charts",
    icon: "PieChart",
    defaultTitle: "Distribution",
    defaultSize: { w: 3, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 6 },
    defaultConfig: { pie_data_source: "fleet_status", doughnut: true },
    component: () => import("./renderers/PieChartRenderer"),
  },
  scatter: {
    type: "scatter",
    label: "Scatter Plot",
    description: "Two-metric correlation chart. Each dot is a device, showing relationship between metrics.",
    category: "charts",
    icon: "ScatterChart",
    defaultTitle: "Correlation",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 3, h: 2 },
    maxSize: { w: 12, h: 6 },
    defaultConfig: { x_metric: "temperature", y_metric: "humidity", time_range: "24h" },
    component: () => import("./renderers/ScatterRenderer"),
  },
  radar: {
    type: "radar",
    label: "Radar Chart",
    description: "Spider chart for multi-metric comparison. See 3-6 metrics at once for fleet health overview.",
    category: "charts",
    icon: "Radar",
    defaultTitle: "Multi-Metric",
    defaultSize: { w: 3, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 6 },
    defaultConfig: { radar_metrics: ["temperature", "humidity", "pressure"], time_range: "24h" },
    component: () => import("./renderers/RadarRenderer"),
  },
```

## Step 3: Expand DISPLAY_OPTIONS

Replace the existing `DISPLAY_OPTIONS` object with this expanded version. This is the key change that gives users real visualization choice:

```typescript
/** Maps widget types to the visualization types they can switch to */
export const DISPLAY_OPTIONS: Record<string, Array<{ value: string; label: string }>> = {
  // Time-series chart widgets can switch between these:
  line_chart: [
    { value: "line", label: "Line Chart" },
    { value: "area", label: "Area Chart" },
    { value: "bar", label: "Bar Chart" },
  ],
  area_chart: [
    { value: "area", label: "Area Chart" },
    { value: "line", label: "Line Chart" },
    { value: "bar", label: "Bar Chart" },
  ],
  bar_chart: [
    { value: "bar", label: "Bar Chart" },
    { value: "line", label: "Line Chart" },
    { value: "area", label: "Area Chart" },
  ],
  // Single-value metric widgets can switch between these:
  kpi_tile: [
    { value: "kpi", label: "KPI Tile" },
    { value: "stat_card", label: "Stat Card" },
    { value: "gauge", label: "Gauge" },
  ],
  stat_card: [
    { value: "stat_card", label: "Stat Card" },
    { value: "kpi", label: "KPI Tile" },
    { value: "gauge", label: "Gauge" },
  ],
  gauge: [
    { value: "gauge", label: "Gauge" },
    { value: "kpi", label: "KPI Tile" },
    { value: "stat_card", label: "Stat Card" },
  ],
  // Scatter has no switching (unique data shape)
  // Radar has no switching (unique data shape)
  // Pie has no switching (unique data source)
  // Table has no switching
  // Alert Feed has no switching
  // Fleet Overview has its own display_mode system
};
```

## Step 4: Expand DISPLAY_RENDERERS

Add the 2 new renderer entries:

```typescript
const DISPLAY_RENDERERS: Record<
  string,
  () => Promise<{ default: ComponentType<WidgetRendererProps> }>
> = {
  line: () => import("./renderers/LineChartRenderer"),
  bar: () => import("./renderers/BarChartRenderer"),
  area: () => import("./renderers/AreaChartRenderer"),
  kpi: () => import("./renderers/KpiTileRenderer"),
  gauge: () => import("./renderers/GaugeRenderer"),
  stat_card: () => import("./renderers/StatCardRenderer"),
};
```

## Step 5: Update AddWidgetDrawer icons

**File:** `frontend/src/features/dashboard/AddWidgetDrawer.tsx`

Add the new Lucide icon imports. If `AreaChart`, `ScatterChart`, or `Radar` don't exist in the installed Lucide version, substitute with available alternatives:

```tsx
import {
  Hash,
  TrendingUp,
  BarChart3,
  Gauge,
  Table2,
  Bell,
  PieChart,
  Cpu,
  Activity,
  AreaChart,
  ScatterChart,
  Radar,
} from "lucide-react";
```

**Important:** If `AreaChart`, `ScatterChart`, or `Radar` are not available in the installed lucide-react version, use these fallbacks:
- `AreaChart` → `TrendingUp` (already imported)
- `ScatterChart` → `Target` or `Circle`
- `Radar` → `Compass` or `Crosshair`

Check available icons with: `grep -r "export.*AreaChart\|export.*ScatterChart\|export.*Radar" node_modules/lucide-react/dist/esm/icons/`

Update the `ICON_MAP` to include all new entries:

```tsx
const ICON_MAP: Record<string, LucideIcon> = {
  Hash,
  TrendingUp,
  BarChart3,
  Gauge,
  Table2,
  Bell,
  PieChart,
  Cpu,
  Activity,
  AreaChart,      // or fallback
  ScatterChart,   // or fallback
  Radar,          // or fallback
};
```

## Step 6: Update category list

**File:** `frontend/src/features/dashboard/widgets/widget-registry.ts`

The `getWidgetsByCategory()` function doesn't need changes — the new widgets use existing categories ("charts" and "metrics") so they'll automatically appear in the right groups.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task: open the Add Widget drawer and verify you see 12 widget types grouped correctly. Verify that line/area/bar chart widgets show 3 Display As options, and KPI/stat card/gauge show 3 Display As options.

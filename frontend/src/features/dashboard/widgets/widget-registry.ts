import type { ComponentType } from "react";
import type { WidgetType } from "@/services/api/dashboards";

export interface WidgetDefinition {
  type: WidgetType;
  label: string;
  description: string;
  category: "charts" | "metrics" | "data" | "fleet";
  icon: string; // lucide icon name
  defaultTitle: string;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  maxSize: { w: number; h: number };
  defaultConfig: Record<string, unknown>;
  component: () => Promise<{ default: ComponentType<WidgetRendererProps> }>;
}

export interface WidgetRendererProps {
  config: Record<string, unknown>;
  title: string;
  widgetId: number;
}

/** Formatting options available in widget config */
export interface WidgetFormatConfig {
  /** Number of decimal places for numeric values (0-4, default: 1) */
  decimal_precision?: number;
  /** Hide the widget title bar (default: false) */
  show_title?: boolean;
  /** Show chart legend (default: true for charts) */
  show_legend?: boolean;
  /** Show X axis labels (default: true) */
  show_x_axis?: boolean;
  /** Show Y axis labels (default: true) */
  show_y_axis?: boolean;
  /** Y axis minimum value (auto if undefined) */
  y_axis_min?: number;
  /** Y axis maximum value (auto if undefined) */
  y_axis_max?: number;
  /** Override visualization type */
  display_as?: string;
  /** Threshold rules for color coding */
  thresholds?: Array<{ value: number; color: string; label?: string }>;
}

export const WIDGET_REGISTRY: Record<string, WidgetDefinition> = {
  kpi_tile: {
    type: "kpi_tile",
    label: "KPI Tile",
    description: "Single metric value with configurable data source. Ideal for at-a-glance monitoring.",
    category: "metrics",
    icon: "Hash",
    defaultTitle: "KPI",
    defaultSize: { w: 2, h: 1 },
    minSize: { w: 1, h: 1 },
    maxSize: { w: 4, h: 2 },
    defaultConfig: { metric: "device_count", aggregation: "count", time_range: "24h" },
    component: () => import("./renderers/KpiTileRenderer"),
  },
  line_chart: {
    type: "line_chart",
    label: "Line Chart",
    description: "Time-series trend line. Track metric changes over configurable time ranges.",
    category: "charts",
    icon: "TrendingUp",
    defaultTitle: "Metric Trend",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 12, h: 6 },
    defaultConfig: { metric: "temperature", time_range: "24h", devices: [] },
    component: () => import("./renderers/LineChartRenderer"),
  },
  bar_chart: {
    type: "bar_chart",
    label: "Bar Chart",
    description: "Grouped bar comparison. Compare metric values across categories or time periods.",
    category: "charts",
    icon: "BarChart3",
    defaultTitle: "Comparison",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 12, h: 6 },
    defaultConfig: { metric: "device_count", group_by: "site", time_range: "24h" },
    component: () => import("./renderers/BarChartRenderer"),
  },
  gauge: {
    type: "gauge",
    label: "Gauge",
    description: "Radial gauge dial showing a value within min/max bounds. Great for utilization metrics.",
    category: "metrics",
    icon: "Gauge",
    defaultTitle: "Fleet Uptime",
    defaultSize: { w: 2, h: 2 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 4, h: 4 },
    defaultConfig: { metric: "uptime_pct", min: 0, max: 100 },
    component: () => import("./renderers/GaugeRenderer"),
  },
  table: {
    type: "table",
    label: "Device Table",
    description: "Sortable device list with status, battery level, and last-seen timestamp.",
    category: "data",
    icon: "Table2",
    defaultTitle: "Devices",
    defaultSize: { w: 6, h: 3 },
    minSize: { w: 3, h: 2 },
    maxSize: { w: 12, h: 8 },
    defaultConfig: { limit: 10, sort_by: "last_seen", filter_status: "" },
    component: () => import("./renderers/TableRenderer"),
  },
  alert_feed: {
    type: "alert_feed",
    label: "Alert Feed",
    description: "Live alert stream from connected devices. Filters by severity level.",
    category: "data",
    icon: "Bell",
    defaultTitle: "Active Alerts",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 8 },
    defaultConfig: { severity_filter: "", max_items: 20 },
    component: () => import("./renderers/AlertFeedRenderer"),
  },
  fleet_overview: {
    type: "fleet_overview",
    label: "Fleet Overview",
    description:
      "Configurable fleet status display. Show device counts, status donut, or health score.",
    category: "fleet",
    icon: "Activity",
    defaultTitle: "Fleet Overview",
    defaultSize: { w: 3, h: 2 },
    minSize: { w: 2, h: 1 },
    maxSize: { w: 6, h: 6 },
    defaultConfig: { display_mode: "count" },
    component: () => import("./renderers/FleetOverviewRenderer"),
  },
  area_chart: {
    type: "area_chart",
    label: "Area Chart",
    description:
      "Filled area chart with gradient. Ideal for showing volume and trends over time. Supports stacking.",
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
    description:
      "Metric value with sparkline trend and directional arrow. At-a-glance monitoring with context.",
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
    description:
      "Proportional breakdown of fleet status, alert severity, or grouped metric data.",
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
    description:
      "Two-metric correlation chart. Each dot is a device, showing relationship between metrics.",
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
    description:
      "Spider chart for multi-metric comparison. See 3-6 metrics at once for fleet health overview.",
    category: "charts",
    icon: "Radar",
    defaultTitle: "Multi-Metric",
    defaultSize: { w: 3, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 6 },
    defaultConfig: { radar_metrics: ["temperature", "humidity", "pressure"], time_range: "24h" },
    component: () => import("./renderers/RadarRenderer"),
  },
};

export function getWidgetDefinition(type: string): WidgetDefinition | undefined {
  // Backward compatibility: map old fleet types to fleet_overview
  const mappedType =
    type === "device_count" || type === "fleet_status" || type === "health_score"
      ? "fleet_overview"
      : type;

  return WIDGET_REGISTRY[mappedType];
}

export function getAllWidgetTypes(): WidgetDefinition[] {
  return Object.values(WIDGET_REGISTRY);
}

export function getWidgetsByCategory(): Array<{
  category: string;
  label: string;
  widgets: WidgetDefinition[];
}> {
  const categories = [
    { category: "charts", label: "Charts" },
    { category: "metrics", label: "Metrics" },
    { category: "data", label: "Data" },
    { category: "fleet", label: "Fleet Overview" },
  ];

  return categories.map((cat) => ({
    ...cat,
    widgets: getAllWidgetTypes().filter((w) => w.category === cat.category),
  }));
}

/** Maps widget types to the visualization types they can switch to */
export const DISPLAY_OPTIONS: Record<string, Array<{ value: string; label: string }>> = {
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
};

/** Maps display_as values to renderer component loaders */
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

/**
 * Get the renderer component loader for a widget, respecting display_as override.
 */
export function getWidgetRenderer(
  widgetType: string,
  config: Record<string, unknown>
): () => Promise<{ default: ComponentType<WidgetRendererProps> }> {
  const displayAs = config.display_as as string | undefined;
  if (displayAs && DISPLAY_RENDERERS[displayAs]) {
    return DISPLAY_RENDERERS[displayAs];
  }

  // Backward compatibility: map old fleet types to fleet_overview renderer
  const mappedType =
    widgetType === "device_count" || widgetType === "fleet_status" || widgetType === "health_score"
      ? "fleet_overview"
      : widgetType;

  const def = WIDGET_REGISTRY[mappedType];
  return def?.component ?? (() => import("./renderers/KpiTileRenderer"));
}


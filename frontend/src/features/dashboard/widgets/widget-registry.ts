import type { ComponentType } from "react";
import type { WidgetType } from "@/services/api/dashboards";

export interface WidgetDefinition {
  type: WidgetType;
  label: string;
  description: string;
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

export const WIDGET_REGISTRY: Record<WidgetType, WidgetDefinition> = {
  kpi_tile: {
    type: "kpi_tile",
    label: "KPI Tile",
    description: "Single metric value with trend indicator",
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
    description: "Time-series line chart for metrics",
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
    description: "Comparison bar chart",
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
    description: "Circular gauge for percentage metrics",
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
    description: "Tabular device list with status",
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
    description: "Live stream of open alerts",
    icon: "Bell",
    defaultTitle: "Active Alerts",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 8 },
    defaultConfig: { severity_filter: "", max_items: 20 },
    component: () => import("./renderers/AlertFeedRenderer"),
  },
  fleet_status: {
    type: "fleet_status",
    label: "Fleet Status",
    description: "Device status donut chart",
    icon: "PieChart",
    defaultTitle: "Fleet Status",
    defaultSize: { w: 3, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 6 },
    defaultConfig: {},
    component: () => import("./renderers/FleetStatusRenderer"),
  },
  device_count: {
    type: "device_count",
    label: "Device Count",
    description: "Total device count with online/offline breakdown",
    icon: "Cpu",
    defaultTitle: "Device Count",
    defaultSize: { w: 2, h: 1 },
    minSize: { w: 1, h: 1 },
    maxSize: { w: 4, h: 2 },
    defaultConfig: {},
    component: () => import("./renderers/DeviceCountRenderer"),
  },
  health_score: {
    type: "health_score",
    label: "Health Score",
    description: "Fleet health overview with status indicators",
    icon: "Activity",
    defaultTitle: "Fleet Health",
    defaultSize: { w: 6, h: 2 },
    minSize: { w: 4, h: 2 },
    maxSize: { w: 12, h: 4 },
    defaultConfig: {},
    component: () => import("./renderers/HealthScoreRenderer"),
  },
};

export function getWidgetDefinition(type: WidgetType): WidgetDefinition | undefined {
  return WIDGET_REGISTRY[type];
}

export function getAllWidgetTypes(): WidgetDefinition[] {
  return Object.values(WIDGET_REGISTRY);
}


import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface DashboardSummary {
  id: number;
  name: string;
  description: string;
  is_default: boolean;
  is_shared: boolean;
  is_owner: boolean;
  widget_count: number;
  created_at: string;
  updated_at: string;
}

export interface WidgetPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

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
  | "health_score";

export interface DashboardWidget {
  id: number;
  widget_type: WidgetType;
  title: string;
  config: Record<string, unknown>;
  position: WidgetPosition;
  created_at: string;
  updated_at: string;
}

export interface Dashboard {
  id: number;
  name: string;
  description: string;
  is_default: boolean;
  is_shared: boolean;
  is_owner: boolean;
  layout: unknown[];
  widgets: DashboardWidget[];
  created_at: string;
  updated_at: string;
}

export interface LayoutItem {
  widget_id: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export async function fetchDashboards(): Promise<{
  dashboards: DashboardSummary[];
  total: number;
}> {
  return apiGet("/api/v1/customer/dashboards");
}

export async function fetchDashboard(id: number): Promise<Dashboard> {
  return apiGet(`/api/v1/customer/dashboards/${id}`);
}

export async function createDashboard(data: {
  name: string;
  description?: string;
  is_default?: boolean;
}): Promise<Dashboard> {
  return apiPost("/api/v1/customer/dashboards", data);
}

export async function updateDashboard(
  id: number,
  data: { name?: string; description?: string; is_default?: boolean }
): Promise<Dashboard> {
  return apiPut(`/api/v1/customer/dashboards/${id}`, data);
}

export async function deleteDashboard(id: number): Promise<void> {
  return apiDelete(`/api/v1/customer/dashboards/${id}`);
}

export async function addWidget(
  dashboardId: number,
  data: {
    widget_type: WidgetType;
    title?: string;
    config?: Record<string, unknown>;
    position?: WidgetPosition;
  }
): Promise<DashboardWidget> {
  return apiPost(`/api/v1/customer/dashboards/${dashboardId}/widgets`, data);
}

export async function updateWidget(
  dashboardId: number,
  widgetId: number,
  data: {
    title?: string;
    config?: Record<string, unknown>;
    position?: WidgetPosition;
  }
): Promise<DashboardWidget> {
  return apiPut(`/api/v1/customer/dashboards/${dashboardId}/widgets/${widgetId}`, data);
}

export async function removeWidget(dashboardId: number, widgetId: number): Promise<void> {
  return apiDelete(`/api/v1/customer/dashboards/${dashboardId}/widgets/${widgetId}`);
}

export async function batchUpdateLayout(
  dashboardId: number,
  layout: LayoutItem[]
): Promise<{ ok: boolean }> {
  return apiPut(`/api/v1/customer/dashboards/${dashboardId}/layout`, { layout });
}

export async function toggleDashboardShare(
  id: number,
  shared: boolean
): Promise<{ id: number; is_shared: boolean }> {
  return apiPut(`/api/v1/customer/dashboards/${id}/share`, { shared });
}

export async function bootstrapDashboard(): Promise<{ id: number; created: boolean }> {
  return apiPost("/api/v1/customer/dashboards/bootstrap", {});
}


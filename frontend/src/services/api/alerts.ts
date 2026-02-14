import { apiGet, apiPatch } from "./client";
import type { AlertListResponse, AlertDetailResponse } from "./types";
import { apiDelete, apiPost, apiPut } from "./client";

export interface AlertTrendPoint {
  hour: string;
  opened: number;
  closed: number;
}

export async function fetchAlerts(
  status = "OPEN",
  limit = 100,
  offset = 0,
  alertType?: string
): Promise<AlertListResponse> {
  let url = `/customer/alerts?status=${status}&limit=${limit}&offset=${offset}`;
  if (alertType) url += `&alert_type=${encodeURIComponent(alertType)}`;
  return apiGet(url);
}

export async function fetchAlert(
  alertId: number
): Promise<AlertDetailResponse> {
  return apiGet(`/api/v2/alerts/${alertId}`);
}

export async function fetchAlertTrend(
  hours = 24
): Promise<{ trend: AlertTrendPoint[] }> {
  return apiGet(`/api/v2/alerts/trend?hours=${hours}`);
}

export async function acknowledgeAlert(alertId: string): Promise<void> {
  await apiPatch(`/customer/alerts/${alertId}/acknowledge`, {});
}

export async function closeAlert(alertId: string): Promise<void> {
  await apiPatch(`/customer/alerts/${alertId}/close`, {});
}

export async function silenceAlert(alertId: string, minutes: number): Promise<void> {
  await apiPatch(`/customer/alerts/${alertId}/silence`, { minutes });
}

export interface MaintenanceWindow {
  window_id: string;
  name: string;
  starts_at: string;
  ends_at: string | null;
  recurring: { dow: number[]; start_hour: number; end_hour: number } | null;
  site_ids: string[] | null;
  device_types: string[] | null;
  enabled: boolean;
  created_at: string;
}

export async function fetchMaintenanceWindows(): Promise<{
  windows: MaintenanceWindow[];
  total: number;
}> {
  return apiGet("/customer/maintenance-windows");
}

export async function createMaintenanceWindow(
  data: Partial<MaintenanceWindow>
): Promise<MaintenanceWindow> {
  return apiPost("/customer/maintenance-windows", data);
}

export async function updateMaintenanceWindow(
  windowId: string,
  data: Partial<MaintenanceWindow>
): Promise<MaintenanceWindow> {
  return apiPatch(`/customer/maintenance-windows/${encodeURIComponent(windowId)}`, data);
}

export async function deleteMaintenanceWindow(windowId: string): Promise<void> {
  await apiDelete(`/customer/maintenance-windows/${encodeURIComponent(windowId)}`);
}

export interface AlertDigestSettings {
  frequency: "daily" | "weekly" | "disabled";
  email: string;
  last_sent_at?: string | null;
}

export async function getAlertDigestSettings(): Promise<AlertDigestSettings> {
  return apiGet("/customer/alert-digest-settings");
}

export async function updateAlertDigestSettings(settings: AlertDigestSettings): Promise<void> {
  await apiPut("/customer/alert-digest-settings", {
    frequency: settings.frequency,
    email: settings.email,
  });
}

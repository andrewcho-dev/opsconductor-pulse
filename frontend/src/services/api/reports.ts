import keycloak from "@/services/auth/keycloak";
import { apiGet } from "./client";

export interface SLASummary {
  period_days: number;
  total_devices: number;
  online_devices: number;
  online_pct: number;
  total_alerts: number;
  unresolved_alerts: number;
  mttr_minutes: number | null;
  top_alerting_devices: Array<{ device_id: string; count: number }>;
}

export interface ReportRun {
  run_id: number;
  report_type: string;
  status: string;
  triggered_by: string;
  row_count: number | null;
  created_at: string;
  completed_at: string | null;
}

async function downloadCsv(path: string, filename: string): Promise<void> {
  if (keycloak.authenticated) await keycloak.updateToken(30);
  const headers: Record<string, string> = {};
  if (keycloak.token) headers.Authorization = `Bearer ${keycloak.token}`;
  const res = await fetch(path, { headers });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportDevicesCSV(): Promise<void> {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  await downloadCsv("/api/v1/customer/export/devices?format=csv", `devices-${date}.csv`);
}

export async function exportAlertsCSV(days: number): Promise<void> {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  await downloadCsv(
    `/api/v1/customer/export/alerts?format=csv&days=${encodeURIComponent(String(days))}`,
    `alerts-${date}.csv`
  );
}

export async function getSLASummary(days = 30): Promise<SLASummary> {
  return apiGet(`/api/v1/customer/reports/sla-summary?days=${encodeURIComponent(String(days))}`);
}

export async function listReportRuns(): Promise<{ runs: ReportRun[] }> {
  return apiGet("/api/v1/customer/reports/runs");
}

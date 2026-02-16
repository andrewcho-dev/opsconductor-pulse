import { apiGet, apiPost } from "./client";
import keycloak from "@/services/auth/keycloak";

export type Aggregation = "avg" | "min" | "max" | "p95" | "sum" | "count";
export type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d";
export type GroupBy = "device" | "site" | "group" | null;

export interface AnalyticsQueryRequest {
  metric: string;
  aggregation: Aggregation;
  time_range: TimeRange;
  group_by: GroupBy;
  device_ids?: string[];
  group_id?: string;
  bucket_size?: string;
}

export interface AnalyticsPoint {
  time: string;
  value: number | null;
}

export interface AnalyticsSeries {
  label: string;
  points: AnalyticsPoint[];
}

export interface AnalyticsSummary {
  min: number | null;
  max: number | null;
  avg: number | null;
  total_points: number;
}

export interface AnalyticsQueryResponse {
  series: AnalyticsSeries[];
  summary: AnalyticsSummary;
}

export interface AvailableMetricsResponse {
  metrics: string[];
}

export async function fetchAvailableMetrics(): Promise<AvailableMetricsResponse> {
  return apiGet("/customer/analytics/metrics");
}

export async function runAnalyticsQuery(
  request: AnalyticsQueryRequest
): Promise<AnalyticsQueryResponse> {
  return apiPost("/customer/analytics/query", request);
}

export async function downloadAnalyticsCSV(request: AnalyticsQueryRequest): Promise<void> {
  if (keycloak.authenticated) {
    await keycloak.updateToken(30);
  }

  const params = new URLSearchParams();
  params.set("metric", request.metric);
  params.set("aggregation", request.aggregation);
  params.set("time_range", request.time_range);
  if (request.group_by) params.set("group_by", request.group_by);
  if (request.device_ids && request.device_ids.length > 0) {
    params.set("device_ids", request.device_ids.join(","));
  }
  if (request.group_id) params.set("group_id", request.group_id);

  const headers: Record<string, string> = {};
  if (keycloak.token) {
    headers.Authorization = `Bearer ${keycloak.token}`;
  }

  const res = await fetch(`/customer/analytics/export?${params.toString()}`, { headers });
  if (!res.ok) {
    throw new Error(`Export failed: ${res.status}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `analytics_${request.metric}_${request.aggregation}_${request.time_range}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}


import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type {
  AlertRule,
  AlertRuleListResponse,
  AlertRuleCreate,
  AlertRuleUpdate,
  MetricCatalogEntry,
  MetricCatalogUpsert,
} from "./types";

export interface AlertRuleTemplate {
  template_id: string;
  device_type: string;
  name: string;
  metric_name: string;
  operator: "GT" | "LT" | "GTE" | "LTE";
  threshold: number;
  severity: number;
  duration_seconds: number;
  description: string;
}

function normalizeRule(rule: AlertRule): AlertRule {
  return {
    ...rule,
    duration_seconds: rule.duration_seconds ?? 0,
  };
}

export async function fetchAlertRules(limit = 100): Promise<AlertRuleListResponse> {
  const res = await apiGet<AlertRuleListResponse>(`/api/v1/customer/alert-rules?limit=${limit}`);
  return {
    ...res,
    rules: (res.rules ?? []).map(normalizeRule),
  };
}

export async function fetchAlertRule(ruleId: string): Promise<AlertRule> {
  const rule = await apiGet<AlertRule>(`/api/v1/customer/alert-rules/${encodeURIComponent(ruleId)}`);
  return normalizeRule(rule);
}

export async function createAlertRule(data: AlertRuleCreate): Promise<AlertRule> {
  const rule = await apiPost<AlertRule>("/api/v1/customer/alert-rules", data);
  return normalizeRule(rule);
}

export async function updateAlertRule(
  ruleId: string,
  data: AlertRuleUpdate
): Promise<AlertRule> {
  const rule = await apiPatch<AlertRule>(`/api/v1/customer/alert-rules/${encodeURIComponent(ruleId)}`, data);
  return normalizeRule(rule);
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  return apiDelete(`/api/v1/customer/alert-rules/${encodeURIComponent(ruleId)}`);
}

export async function fetchAlertRuleTemplates(
  deviceType?: string
): Promise<AlertRuleTemplate[]> {
  const params = deviceType ? `?device_type=${encodeURIComponent(deviceType)}` : "";
  const res = await apiGet<{ templates: AlertRuleTemplate[] }>(
    `/api/v1/customer/alert-rule-templates${params}`
  );
  return res.templates ?? [];
}

export async function applyAlertRuleTemplates(
  templateIds: string[],
  siteIds?: string[]
): Promise<{ created: Array<{ id: number; name: string; template_id: string }>; skipped: string[] }> {
  return apiPost("/api/v1/customer/alert-rule-templates/apply", {
    template_ids: templateIds,
    site_ids: siteIds,
  });
}

export async function fetchMetricCatalog(): Promise<{
  tenant_id: string;
  metrics: MetricCatalogEntry[];
}> {
  return apiGet("/api/v1/customer/metrics/catalog");
}

export async function upsertMetricCatalog(
  payload: MetricCatalogUpsert
): Promise<{ tenant_id: string; metric: MetricCatalogEntry }> {
  return apiPost("/api/v1/customer/metrics/catalog", payload);
}

export async function deleteMetricCatalog(metricName: string): Promise<void> {
  return apiDelete(`/api/v1/customer/metrics/catalog/${encodeURIComponent(metricName)}`);
}

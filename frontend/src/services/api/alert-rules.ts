import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type {
  AlertRule,
  AlertRuleListResponse,
  AlertRuleCreate,
  AlertRuleUpdate,
} from "./types";

export async function fetchAlertRules(limit = 100): Promise<AlertRuleListResponse> {
  return apiGet(`/api/v2/alert-rules?limit=${limit}`);
}

export async function fetchAlertRule(ruleId: string): Promise<AlertRule> {
  return apiGet(`/customer/alert-rules/${encodeURIComponent(ruleId)}`);
}

export async function createAlertRule(data: AlertRuleCreate): Promise<AlertRule> {
  return apiPost("/customer/alert-rules", data);
}

export async function updateAlertRule(
  ruleId: string,
  data: AlertRuleUpdate
): Promise<AlertRule> {
  return apiPatch(`/customer/alert-rules/${encodeURIComponent(ruleId)}`, data);
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  return apiDelete(`/customer/alert-rules/${encodeURIComponent(ruleId)}`);
}

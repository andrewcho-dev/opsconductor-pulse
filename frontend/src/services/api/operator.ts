import { apiGet, apiPost } from "./client";
import type {
  OperatorDevicesResponse,
  OperatorAlertsResponse,
  QuarantineResponse,
  OperatorIntegrationsResponse,
  AuditLogResponse,
} from "./types";

export async function fetchOperatorDevices(
  tenantFilter?: string,
  limit = 100,
  offset = 0
): Promise<OperatorDevicesResponse> {
  let url = `/operator/devices?limit=${limit}&offset=${offset}`;
  if (tenantFilter) url += `&tenant_filter=${encodeURIComponent(tenantFilter)}`;
  return apiGet(url);
}

export async function fetchOperatorAlerts(
  status = "OPEN",
  tenantFilter?: string,
  limit = 100
): Promise<OperatorAlertsResponse> {
  let url = `/operator/alerts?status=${status}&limit=${limit}`;
  if (tenantFilter) url += `&tenant_filter=${encodeURIComponent(tenantFilter)}`;
  return apiGet(url);
}

export async function fetchQuarantine(
  minutes = 60,
  limit = 100
): Promise<QuarantineResponse> {
  return apiGet(`/operator/quarantine?minutes=${minutes}&limit=${limit}`);
}

export async function fetchOperatorIntegrations(
  tenantFilter?: string
): Promise<OperatorIntegrationsResponse> {
  let url = "/operator/integrations";
  if (tenantFilter) url += `?tenant_filter=${encodeURIComponent(tenantFilter)}`;
  return apiGet(url);
}

export async function fetchAuditLog(
  userId?: string,
  action?: string,
  since?: string,
  limit = 100
): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (userId) params.set("user_id", userId);
  if (action) params.set("action", action);
  if (since) params.set("since", since);
  return apiGet(`/operator/audit-log?${params.toString()}`);
}

export async function updateOperatorSettings(data: {
  mode: string;
  store_rejects: string;
  mirror_rejects: string;
}): Promise<void> {
  // Backend expects form data for settings POST
  return apiPost("/operator/settings", data);
}

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
  limit = 100,
  offset = 0
): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  params.set("source", "operator");  // Request operator access log
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (userId) params.set("user_id", userId);
  if (action) params.set("action", action);
  if (since) params.set("since", since);
  return apiGet(`/operator/audit-log?${params.toString()}`);
}

export interface ActivityLogFilters {
  tenantId?: string;
  category?: string;
  severity?: string;
  entityType?: string;
  search?: string;
  start?: string;
  end?: string;
  limit?: number;
  offset?: number;
}

export interface ActivityLogEvent {
  timestamp: string;
  tenant_id: string;
  event_type: string;
  category: string;
  severity: string;
  entity_type: string | null;
  entity_id: string | null;
  entity_name: string | null;
  action: string;
  message: string;
  details: Record<string, unknown> | null;
  source_service: string | null;
  actor_type: string | null;
  actor_id: string | null;
  actor_name: string | null;
}

export interface ActivityLogResponse {
  events: ActivityLogEvent[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchActivityLog(filters: ActivityLogFilters): Promise<ActivityLogResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit || 100));
  params.set("offset", String(filters.offset || 0));
  if (filters.tenantId) params.set("tenant_id", filters.tenantId);
  if (filters.category) params.set("category", filters.category);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.entityType) params.set("entity_type", filters.entityType);
  if (filters.search) params.set("search", filters.search);
  if (filters.start) params.set("start", filters.start);
  if (filters.end) params.set("end", filters.end);
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

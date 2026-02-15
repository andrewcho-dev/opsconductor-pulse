import { apiDelete, apiGet, apiPost, apiPatch } from "./client";
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

export interface KeycloakUser {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  enabled: boolean;
  emailVerified: boolean;
  createdTimestamp?: number;
  roles?: string[];
}

export async function fetchUsers(params?: {
  search?: string;
  first?: number;
  max?: number;
}): Promise<{ users: KeycloakUser[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.search) qs.set("search", params.search);
  if (params?.first != null) qs.set("first", String(params.first));
  if (params?.max != null) qs.set("max_results", String(params.max));
  return apiGet(`/operator/users${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function createUser(data: {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  temporary_password: string;
  enabled?: boolean;
}): Promise<KeycloakUser> {
  return apiPost("/operator/users", data);
}

export async function deleteUser(userId: string): Promise<void> {
  await apiDelete(`/operator/users/${encodeURIComponent(userId)}`);
}

export async function sendPasswordReset(userId: string): Promise<void> {
  await apiPost(`/operator/users/${encodeURIComponent(userId)}/reset-password`, {});
}

export async function fetchUserDetail(userId: string): Promise<KeycloakUser> {
  return apiGet(`/operator/users/${encodeURIComponent(userId)}`);
}

export async function updateUser(
  userId: string,
  updates: Partial<{
    first_name: string;
    last_name: string;
    enabled: boolean;
    email_verified: boolean;
  }>
): Promise<void> {
  await apiPatch(`/operator/users/${encodeURIComponent(userId)}`, updates);
}

export async function resetUserPassword(
  userId: string,
  password: string,
  temporary: boolean
): Promise<void> {
  await apiPost(`/operator/users/${encodeURIComponent(userId)}/reset-password`, {
    password,
    temporary,
  });
}

export async function assignRole(userId: string, roleName: string): Promise<void> {
  await apiPost(`/operator/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(roleName)}`, {});
}

export async function removeRole(userId: string, roleName: string): Promise<void> {
  await apiDelete(
    `/operator/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(roleName)}`,
  );
}

export interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  created_at: string;
}

export interface SystemMetricsSnapshot {
  ingest?: Record<string, number>;
  evaluator?: Record<string, number>;
  dispatcher?: Record<string, number>;
  delivery?: Record<string, number>;
  [key: string]: unknown;
}

export interface MetricsHistoryPoint {
  time: string;
  value: number;
}

export async function fetchSystemMetricsLatest(): Promise<SystemMetricsSnapshot> {
  return apiGet("/operator/system/metrics/latest");
}

export async function fetchSystemMetricsHistory(params?: {
  metric?: string;
  minutes?: number;
  service?: string;
  rate?: boolean;
}): Promise<{ metric: string; service?: string | null; points: MetricsHistoryPoint[]; minutes: number; rate: boolean }> {
  const searchParams = new URLSearchParams();
  if (params?.metric) searchParams.set("metric", params.metric);
  if (params?.minutes != null) searchParams.set("minutes", String(params.minutes));
  if (params?.service) searchParams.set("service", params.service);
  if (params?.rate != null) searchParams.set("rate", String(params.rate));
  return apiGet(`/operator/system/metrics/history${searchParams.toString() ? `?${searchParams.toString()}` : ""}`);
}

export interface TenantStats {
  tenant_id: string;
  device_count?: number;
  active_alert_count?: number;
  subscription_count?: number;
  [key: string]: unknown;
}

export interface Subscription {
  subscription_id: string;
  tenant_id: string;
  subscription_type: string;
  status: string;
  device_limit: number | null;
  term_end: string | null;
  description: string | null;
  created_at?: string;
}

export interface ExpiryNotification {
  id: string | number;
  tenant_id: string;
  notification_type: string;
  scheduled_at: string;
  sent_at: string | null;
  channel: string | null;
  status: string;
  error: string | null;
}

export async function fetchExpiryNotifications(params?: {
  status?: string;
  tenant_id?: string;
  limit?: number;
}): Promise<{ notifications: ExpiryNotification[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.tenant_id) searchParams.set("tenant_id", params.tenant_id);
  if (params?.limit != null) searchParams.set("limit", String(params.limit));
  return apiGet(
    `/operator/subscriptions/expiring-notifications${
      searchParams.toString() ? `?${searchParams.toString()}` : ""
    }`
  );
}

export interface AuditEvent {
  id: string | number;
  tenant_id: string;
  category: string;
  severity: string;
  entity_type: string;
  entity_id: string;
  message: string;
  created_at: string;
}

export async function fetchOperatorTenants(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ tenants: Tenant[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.offset != null) sp.set("offset", String(params.offset));
  return apiGet(`/operator/tenants${sp.toString() ? `?${sp.toString()}` : ""}`);
}

export async function fetchTenantDetail(tenantId: string): Promise<Tenant> {
  return apiGet(`/operator/tenants/${encodeURIComponent(tenantId)}`);
}

export async function fetchTenantStats(tenantId: string): Promise<TenantStats> {
  return apiGet(`/operator/tenants/${encodeURIComponent(tenantId)}/stats`);
}

export async function createTenant(data: { name: string; [key: string]: unknown }): Promise<Tenant> {
  return apiPost("/operator/tenants", data);
}

export async function updateTenant(
  tenantId: string,
  data: Partial<Tenant>
): Promise<Tenant> {
  return apiPatch(`/operator/tenants/${encodeURIComponent(tenantId)}`, data);
}

export async function fetchSubscriptions(params?: {
  tenant_id?: string;
  status?: string;
  limit?: number;
}): Promise<{ subscriptions: Subscription[] }> {
  const sp = new URLSearchParams();
  if (params?.tenant_id) sp.set("tenant_id", params.tenant_id);
  if (params?.status) sp.set("status", params.status);
  if (params?.limit != null) sp.set("limit", String(params.limit));
  return apiGet(`/operator/subscriptions${sp.toString() ? `?${sp.toString()}` : ""}`);
}

export async function createSubscription(data: {
  tenant_id: string;
  subscription_type: string;
  device_limit?: number;
  term_end?: string;
  description?: string;
}): Promise<Subscription> {
  return apiPost("/operator/subscriptions", data);
}

export async function updateSubscription(
  subscriptionId: string,
  data: Partial<Subscription>
): Promise<Subscription> {
  return apiPatch(`/operator/subscriptions/${encodeURIComponent(subscriptionId)}`, data);
}

import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "./client";
import keycloak from "@/services/auth/keycloak";
import type {
  DeviceListResponse,
  DeviceDetailResponse,
  FleetSummary,
  DeviceUpdate,
  DeviceTagsResponse,
  AllTagsResponse,
} from "./types";

export interface DeviceListParams {
  limit?: number;
  offset?: number;
  status?: string;
  tags?: string[];
  tag?: string;
  search?: string;
  q?: string;
  site_id?: string;
}

export interface ProvisionDeviceRequest {
  name: string;
  device_type: string;
  site_id?: string;
  tags?: string[];
}

export interface ProvisionDeviceResponse {
  device_id: string;
  client_id: string;
  password: string;
  broker_url: string;
}

export interface TelemetryHistoryPoint {
  time: string;
  avg: number | null;
  min: number | null;
  max: number | null;
  count: number;
}

export interface TelemetryHistoryResponse {
  device_id: string;
  metric: string;
  range: "1h" | "6h" | "24h" | "7d" | "30d";
  bucket_size: string;
  points: TelemetryHistoryPoint[];
}

export interface TwinDesired {
  [key: string]: unknown;
}

export interface TwinDocument {
  device_id: string;
  desired: TwinDesired;
  reported: Record<string, unknown>;
  delta: Record<string, unknown>;
  desired_version: number;
  reported_version: number;
  sync_status: "synced" | "pending" | "stale";
  shadow_updated_at: string | null;
}

export type CommandStatus = "queued" | "delivered" | "missed" | "expired";

export interface DeviceCommand {
  command_id: string;
  command_type: string;
  command_params: Record<string, unknown>;
  status: CommandStatus;
  published_at: string | null;
  acked_at: string | null;
  expires_at: string;
  created_by: string | null;
  created_at: string;
}

export interface SendCommandPayload {
  command_type: string;
  command_params: Record<string, unknown>;
  expires_in_minutes?: number;
}

export async function fetchDevices(
  params: DeviceListParams = {}
): Promise<DeviceListResponse> {
  const { limit = 100, offset = 0, status, tags, tag, search, q, site_id } = params;
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(limit));
  searchParams.set("offset", String(offset));
  if (status) searchParams.set("status", status);
  if (tags && tags.length > 0) searchParams.set("tags", tags.join(","));
  if (tag) searchParams.set("tag", tag);
  if (search) searchParams.set("search", search);
  if (q) searchParams.set("q", q);
  if (site_id) searchParams.set("site_id", site_id);

  return apiGet(`/api/v2/devices?${searchParams.toString()}`);
}

export async function fetchDevice(
  deviceId: string
): Promise<DeviceDetailResponse> {
  return apiGet(`/api/v2/devices/${encodeURIComponent(deviceId)}`);
}

export async function fetchFleetSummary(): Promise<FleetSummary> {
  return apiGet("/customer/devices/summary");
}

export async function updateDevice(
  deviceId: string,
  update: DeviceUpdate
): Promise<DeviceDetailResponse> {
  return apiPatch(`/customer/devices/${encodeURIComponent(deviceId)}`, update);
}

export async function provisionDevice(
  req: ProvisionDeviceRequest
): Promise<ProvisionDeviceResponse> {
  const deviceId = req.name.trim().replace(/\s+/g, "-").toUpperCase();
  const created = await apiPost<{ device_id: string; status: string }>(
    "/customer/devices",
    {
      device_id: deviceId,
      site_id: req.site_id || "default-site",
    }
  );

  if (req.tags && req.tags.length > 0) {
    await setDeviceTags(created.device_id, req.tags);
  }

  // Provision API credentials are one-time in production; this is a UI bootstrap fallback.
  return {
    device_id: created.device_id,
    client_id: created.device_id,
    password: `tok-${created.device_id.toLowerCase()}`,
    broker_url: "mqtt://localhost:1883",
  };
}

export async function decommissionDevice(deviceId: string): Promise<void> {
  await apiPatch(`/customer/devices/${encodeURIComponent(deviceId)}/decommission`, {});
}

export async function getDeviceTwin(
  deviceId: string
): Promise<TwinDocument & { etag: string }> {
  const token = keycloak.token;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`/customer/devices/${encodeURIComponent(deviceId)}/twin`, {
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to load twin: ${res.status}`);
  }
  const data = (await res.json()) as TwinDocument;
  const etag = res.headers.get("ETag") ?? `"${data.desired_version}"`;
  return { ...data, etag };
}

export class ConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConflictError";
  }
}

export async function updateDesiredState(
  deviceId: string,
  desired: TwinDesired,
  etag: string
): Promise<{ device_id: string; desired: TwinDesired; desired_version: number }> {
  const token = keycloak.token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "If-Match": etag,
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`/customer/devices/${encodeURIComponent(deviceId)}/twin/desired`, {
    method: "PATCH",
    headers,
    body: JSON.stringify({ desired }),
  });
  if (res.status === 409) {
    throw new ConflictError("Another user modified this twin. Refresh to see latest.");
  }
  if (res.status === 428) {
    throw new Error("Version header required. Please refresh the twin first.");
  }
  if (!res.ok) {
    throw new Error(`Failed to update twin: ${res.status}`);
  }
  return res.json();
}

export interface ConnectionEvent {
  id: string;
  event_type: "CONNECTED" | "DISCONNECTED" | "CONNECTION_LOST";
  timestamp: string;
  details: Record<string, unknown>;
}

export interface ConnectionEventsResponse {
  device_id: string;
  events: ConnectionEvent[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchDeviceConnections(
  deviceId: string,
  limit = 50,
  offset = 0
): Promise<ConnectionEventsResponse> {
  return apiGet(
    `/customer/devices/${encodeURIComponent(deviceId)}/connections?limit=${limit}&offset=${offset}`
  );
}

export async function sendCommand(
  deviceId: string,
  payload: SendCommandPayload
): Promise<{ command_id: string; status: string; mqtt_published: boolean }> {
  return apiPost(`/customer/devices/${encodeURIComponent(deviceId)}/commands`, payload);
}

export async function listDeviceCommands(
  deviceId: string,
  status?: string
): Promise<DeviceCommand[]> {
  const path = status
    ? `/customer/devices/${encodeURIComponent(deviceId)}/commands?status=${encodeURIComponent(status)}`
    : `/customer/devices/${encodeURIComponent(deviceId)}/commands`;
  return apiGet(path);
}

export async function getDeviceTags(deviceId: string): Promise<DeviceTagsResponse> {
  return apiGet(`/customer/devices/${encodeURIComponent(deviceId)}/tags`);
}

export async function setDeviceTags(
  deviceId: string,
  tags: string[]
): Promise<DeviceTagsResponse> {
  return apiPut(`/customer/devices/${encodeURIComponent(deviceId)}/tags`, { tags });
}

export async function addDeviceTag(
  deviceId: string,
  tag: string
): Promise<{ tenant_id: string; device_id: string; tag: string }> {
  return apiPost(
    `/customer/devices/${encodeURIComponent(deviceId)}/tags/${encodeURIComponent(tag)}`,
    {}
  );
}

export async function removeDeviceTag(
  deviceId: string,
  tag: string
): Promise<void> {
  return apiDelete(
    `/customer/devices/${encodeURIComponent(deviceId)}/tags/${encodeURIComponent(tag)}`
  );
}

export async function getAllTags(): Promise<AllTagsResponse> {
  return apiGet("/customer/tags");
}

export async function geocodeAddress(address: string): Promise<{
  latitude?: number;
  longitude?: number;
  display_name?: string;
  error?: string;
}> {
  return apiGet(`/customer/geocode?address=${encodeURIComponent(address)}`);
}

export async function fetchTelemetryHistory(
  deviceId: string,
  metric: string,
  range: "1h" | "6h" | "24h" | "7d" | "30d"
): Promise<TelemetryHistoryResponse> {
  return apiGet(
    `/customer/devices/${encodeURIComponent(deviceId)}/telemetry/history?metric=${encodeURIComponent(
      metric
    )}&range=${range}`
  );
}

export async function downloadTelemetryCSV(
  deviceId: string,
  range: "1h" | "6h" | "24h" | "7d" | "30d"
): Promise<void> {
  if (keycloak.authenticated) {
    await keycloak.updateToken(30);
  }
  const headers: Record<string, string> = {};
  if (keycloak.token) {
    headers.Authorization = `Bearer ${keycloak.token}`;
  }
  const res = await fetch(
    `/customer/devices/${encodeURIComponent(deviceId)}/telemetry/export?range=${encodeURIComponent(range)}`,
    { headers }
  );
  if (!res.ok) {
    throw new Error(`Export failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${deviceId}_telemetry_${range}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export interface DeviceGroup {
  group_id: string;
  name: string;
  description: string | null;
  member_count: number | null;
  group_type?: "static" | "dynamic";
  query_filter?: Record<string, unknown>;
  created_at: string;
}

export interface DeviceGroupMember {
  device_id: string;
  name: string;
  status: string;
  site_id: string;
  added_at?: string;
}

export interface DeviceToken {
  id: string;
  client_id: string;
  label: string;
  created_at: string;
  revoked_at: string | null;
}

export interface ImportResultRow {
  row: number;
  name: string;
  status: "ok" | "error";
  device_id?: string;
  message?: string;
}

export interface ImportResult {
  total: number;
  imported: number;
  failed: number;
  results: ImportResultRow[];
}

export interface DeviceUptimeStats {
  device_id: string;
  range: "24h" | "7d" | "30d" | string;
  uptime_pct: number;
  offline_seconds: number;
  range_seconds: number;
  status: "online" | "offline";
}

export interface FleetUptimeSummary {
  total_devices: number;
  online: number;
  offline: number;
  avg_uptime_pct: number;
  as_of: string;
}

export async function fetchDeviceGroups(): Promise<{ groups: DeviceGroup[]; total: number }> {
  return apiGet("/customer/device-groups");
}

export async function createDeviceGroup(data: {
  name: string;
  description?: string;
}): Promise<DeviceGroup> {
  return apiPost("/customer/device-groups", data);
}

export async function updateDeviceGroup(
  groupId: string,
  data: { name?: string; description?: string }
): Promise<DeviceGroup> {
  return apiPatch(`/customer/device-groups/${encodeURIComponent(groupId)}`, data);
}

export async function deleteDeviceGroup(groupId: string): Promise<void> {
  await apiDelete(`/customer/device-groups/${encodeURIComponent(groupId)}`);
}

export async function fetchGroupMembers(
  groupId: string
): Promise<{ group_id: string; members: DeviceGroupMember[]; total: number }> {
  return apiGet(`/customer/device-groups/${encodeURIComponent(groupId)}/devices`);
}

export async function addGroupMember(groupId: string, deviceId: string): Promise<void> {
  await apiPut(
    `/customer/device-groups/${encodeURIComponent(groupId)}/devices/${encodeURIComponent(deviceId)}`,
    {}
  );
}

export async function removeGroupMember(groupId: string, deviceId: string): Promise<void> {
  await apiDelete(
    `/customer/device-groups/${encodeURIComponent(groupId)}/devices/${encodeURIComponent(deviceId)}`
  );
}

export interface DynamicDeviceGroup {
  group_id: string;
  name: string;
  description: string | null;
  query_filter: Record<string, unknown>;
  group_type: "dynamic";
  created_at: string;
}

export interface DynamicGroupFilter {
  status?: string;
  tags?: string[];
  site_id?: string;
}

export async function createDynamicGroup(data: {
  name: string;
  description?: string;
  query_filter: DynamicGroupFilter;
}): Promise<DynamicDeviceGroup> {
  return apiPost("/customer/device-groups/dynamic", data);
}

export async function updateDynamicGroup(
  groupId: string,
  data: { name?: string; description?: string; query_filter?: DynamicGroupFilter }
): Promise<DynamicDeviceGroup> {
  return apiPatch(`/customer/device-groups/${encodeURIComponent(groupId)}/dynamic`, data);
}

export async function deleteDynamicGroup(groupId: string): Promise<void> {
  await apiDelete(`/customer/device-groups/${encodeURIComponent(groupId)}/dynamic`);
}

export async function fetchGroupMembersV2(
  groupId: string
): Promise<{ group_id: string; group_type: string; members: DeviceGroupMember[]; total: number }> {
  return apiGet(`/customer/device-groups/${encodeURIComponent(groupId)}/members`);
}

export async function listDeviceTokens(
  deviceId: string
): Promise<{ device_id: string; tokens: DeviceToken[]; total: number }> {
  return apiGet(`/customer/devices/${encodeURIComponent(deviceId)}/tokens`);
}

export async function revokeDeviceToken(deviceId: string, tokenId: string): Promise<void> {
  await apiDelete(
    `/customer/devices/${encodeURIComponent(deviceId)}/tokens/${encodeURIComponent(tokenId)}`
  );
}

export async function rotateDeviceToken(
  deviceId: string,
  label = "rotated"
): Promise<ProvisionDeviceResponse> {
  return apiPost(`/customer/devices/${encodeURIComponent(deviceId)}/tokens/rotate`, { label });
}

export async function importDevicesCSV(file: File): Promise<ImportResult> {
  if (keycloak.authenticated) {
    await keycloak.updateToken(30);
  }
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/customer/devices/import", {
    method: "POST",
    body: form,
    headers: keycloak.token ? { Authorization: `Bearer ${keycloak.token}` } : undefined,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Import failed: ${response.status}`);
  }
  return response.json();
}

export async function getDeviceUptime(
  deviceId: string,
  range: "24h" | "7d" | "30d"
): Promise<DeviceUptimeStats> {
  return apiGet(
    `/customer/devices/${encodeURIComponent(deviceId)}/uptime?range=${encodeURIComponent(range)}`
  );
}

export async function getFleetUptimeSummary(): Promise<FleetUptimeSummary> {
  return apiGet("/customer/fleet/uptime-summary");
}

export interface FleetHealthResponse {
  score: number;
  total_devices: number;
  online: number;
  critical_alerts: number;
  calculated_at: string;
}

export async function fetchFleetHealth(): Promise<FleetHealthResponse> {
  return apiGet("/customer/fleet/health");
}

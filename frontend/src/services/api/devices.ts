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

export async function fetchDevices(
  params: DeviceListParams = {}
): Promise<DeviceListResponse> {
  const { limit = 100, offset = 0, status, tags, q, site_id } = params;
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(limit));
  searchParams.set("offset", String(offset));
  if (status) searchParams.set("status", status);
  if (tags && tags.length > 0) searchParams.set("tags", tags.join(","));
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
  member_count: number;
  created_at: string;
}

export interface DeviceGroupMember {
  device_id: string;
  name: string;
  status: string;
  site_id: string;
  added_at: string;
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

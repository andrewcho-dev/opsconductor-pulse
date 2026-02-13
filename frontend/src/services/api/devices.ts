import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "./client";
import type {
  DeviceListResponse,
  DeviceDetailResponse,
  FleetSummary,
  DeviceUpdate,
  DeviceTagsResponse,
  AllTagsResponse,
} from "./types";

export async function fetchDevices(
  limit = 100,
  offset = 0
): Promise<DeviceListResponse> {
  return apiGet(`/api/v2/devices?limit=${limit}&offset=${offset}`);
}

export async function fetchDevice(
  deviceId: string
): Promise<DeviceDetailResponse> {
  return apiGet(`/api/v2/devices/${encodeURIComponent(deviceId)}`);
}

export async function fetchFleetSummary(): Promise<FleetSummary> {
  return apiGet("/api/v2/fleet/summary");
}

export async function updateDevice(
  deviceId: string,
  update: DeviceUpdate
): Promise<DeviceDetailResponse> {
  return apiPatch(`/customer/devices/${encodeURIComponent(deviceId)}`, update);
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

import { apiGet } from "./client";
import type { DeviceListResponse, DeviceDetailResponse } from "./types";

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

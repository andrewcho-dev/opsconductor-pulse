import { apiGet } from "./client";
import type { TelemetryResponse } from "./types";

export async function fetchTelemetry(
  deviceId: string,
  start?: string,
  end?: string,
  limit = 120
): Promise<TelemetryResponse> {
  let url = `/api/v2/devices/${encodeURIComponent(deviceId)}/telemetry?limit=${limit}`;
  if (start) url += `&start=${encodeURIComponent(start)}`;
  if (end) url += `&end=${encodeURIComponent(end)}`;
  return apiGet(url);
}

export async function fetchLatestTelemetry(
  deviceId: string,
  count = 1
): Promise<TelemetryResponse> {
  return apiGet(
    `/api/v2/devices/${encodeURIComponent(deviceId)}/telemetry/latest?count=${count}`
  );
}

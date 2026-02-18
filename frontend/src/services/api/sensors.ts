import { apiDelete, apiGet, apiPost, apiPut } from "./client";
import type {
  ConnectionUpsert,
  DeviceConnection,
  DeviceHealthPoint,
  DeviceHealthResponse,
  Sensor,
  SensorCreate,
  SensorListResponse,
  SensorUpdate,
} from "./types";

// ─── Sensors ─────────────────────────────────────────

export async function listDeviceSensors(deviceId: string): Promise<SensorListResponse> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/sensors`);
}

export async function listAllSensors(
  params: {
    sensor_type?: string;
    status?: string;
    device_id?: string;
    limit?: number;
    offset?: number;
  } = {},
): Promise<SensorListResponse> {
  const search = new URLSearchParams();
  if (params.sensor_type) search.set("sensor_type", params.sensor_type);
  if (params.status) search.set("status", params.status);
  if (params.device_id) search.set("device_id", params.device_id);
  if (params.limit) search.set("limit", String(params.limit));
  if (params.offset) search.set("offset", String(params.offset));
  const qs = search.toString();
  return apiGet(`/api/v1/customer/sensors${qs ? `?${qs}` : ""}`);
}

export async function createSensor(deviceId: string, data: SensorCreate): Promise<Sensor> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/sensors`, data);
}

export async function updateSensor(sensorId: number, data: SensorUpdate): Promise<Sensor> {
  return apiPut(`/api/v1/customer/sensors/${sensorId}`, data);
}

export async function deleteSensor(sensorId: number): Promise<void> {
  return apiDelete(`/api/v1/customer/sensors/${sensorId}`);
}

// ─── Device Connections ──────────────────────────────

export async function getDeviceConnection(
  deviceId: string,
): Promise<{ device_id: string; connection: DeviceConnection | null }> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/connection`);
}

export async function upsertDeviceConnection(
  deviceId: string,
  data: ConnectionUpsert,
): Promise<DeviceConnection> {
  return apiPut(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/connection`, data);
}

export async function deleteDeviceConnection(deviceId: string): Promise<void> {
  return apiDelete(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/connection`);
}

// ─── Device Health ───────────────────────────────────

export async function getDeviceHealth(
  deviceId: string,
  range: "1h" | "6h" | "24h" | "7d" | "30d" = "24h",
  limit = 100,
): Promise<DeviceHealthResponse> {
  return apiGet(
    `/api/v1/customer/devices/${encodeURIComponent(deviceId)}/health?range=${range}&limit=${limit}`,
  );
}

export async function getDeviceHealthLatest(deviceId: string): Promise<DeviceHealthPoint | null> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/health/latest`);
}


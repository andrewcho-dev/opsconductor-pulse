# Task 001 — Sensor API Functions & TypeScript Types

## Files

1. Create `frontend/src/services/api/sensors.ts`
2. Update `frontend/src/services/api/types.ts`

## Types to Add (in `types.ts`)

```typescript
// ─── Sensor Types ────────────────────────────────────

export interface Sensor {
  sensor_id: number;
  device_id: string;
  metric_name: string;
  sensor_type: string;
  label: string | null;
  unit: string | null;
  min_range: number | null;
  max_range: number | null;
  precision_digits: number;
  status: "active" | "disabled" | "stale" | "error";
  auto_discovered: boolean;
  last_value: number | null;
  last_seen_at: string | null;
  created_at: string;
}

export interface SensorListResponse {
  device_id?: string;
  sensors: Sensor[];
  total: number;
  sensor_limit?: number;
}

export interface SensorCreate {
  metric_name: string;
  sensor_type: string;
  label?: string;
  unit?: string;
  min_range?: number;
  max_range?: number;
  precision_digits?: number;
}

export interface SensorUpdate {
  sensor_type?: string;
  label?: string;
  unit?: string;
  min_range?: number;
  max_range?: number;
  precision_digits?: number;
  status?: "active" | "disabled";
}

// ─── Device Connection Types ─────────────────────────

export interface DeviceConnection {
  device_id: string;
  connection_type: "cellular" | "ethernet" | "wifi" | "lora" | "satellite" | "other";
  carrier_name: string | null;
  carrier_account_id: string | null;
  plan_name: string | null;
  apn: string | null;
  sim_iccid: string | null;
  sim_status: "active" | "suspended" | "deactivated" | "ready" | "unknown" | null;
  data_limit_mb: number | null;
  data_used_mb: number | null;
  data_used_updated_at: string | null;
  billing_cycle_start: number | null;
  ip_address: string | null;
  msisdn: string | null;
  network_status: "connected" | "disconnected" | "suspended" | "unknown" | null;
  last_network_attach: string | null;
}

export interface ConnectionUpsert {
  connection_type?: string;
  carrier_name?: string;
  carrier_account_id?: string;
  plan_name?: string;
  apn?: string;
  sim_iccid?: string;
  sim_status?: string;
  data_limit_mb?: number;
  billing_cycle_start?: number;
  ip_address?: string;
  msisdn?: string;
}

// ─── Device Health Types ─────────────────────────────

export interface DeviceHealthPoint {
  time: string;
  rssi: number | null;
  rsrp: number | null;
  rsrq: number | null;
  sinr: number | null;
  signal_quality: number | null;
  network_type: string | null;
  cell_id: string | null;
  battery_pct: number | null;
  battery_voltage: number | null;
  power_source: string | null;
  charging: boolean | null;
  cpu_temp_c: number | null;
  memory_used_pct: number | null;
  storage_used_pct: number | null;
  uptime_seconds: number | null;
  reboot_count: number | null;
  error_count: number | null;
  data_tx_bytes: number | null;
  data_rx_bytes: number | null;
  gps_lat: number | null;
  gps_lon: number | null;
  gps_fix: boolean | null;
}

export interface DeviceHealthResponse {
  device_id: string;
  range: string;
  data_points: DeviceHealthPoint[];
  total: number;
  latest: DeviceHealthPoint | null;
}
```

## API Functions (in new `sensors.ts`)

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import type {
  Sensor,
  SensorListResponse,
  SensorCreate,
  SensorUpdate,
  DeviceConnection,
  ConnectionUpsert,
  DeviceHealthResponse,
  DeviceHealthPoint,
} from "./types";

// ─── Sensors ─────────────────────────────────────────

export async function listDeviceSensors(deviceId: string): Promise<SensorListResponse> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/sensors`);
}

export async function listAllSensors(params: {
  sensor_type?: string;
  status?: string;
  device_id?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<SensorListResponse> {
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

export async function getDeviceConnection(deviceId: string): Promise<{ device_id: string; connection: DeviceConnection | null }> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/connection`);
}

export async function upsertDeviceConnection(deviceId: string, data: ConnectionUpsert): Promise<DeviceConnection> {
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
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

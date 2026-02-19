# Task 1: Update TypeScript Types for New Response Shapes

## Modify file: `frontend/src/services/api/types.ts`

Add types that match the updated backend response shapes from Phase 169.

### New Types to Add

```typescript
// ─── Device Module Types ───────────────────────────────

export interface DeviceModule {
  id: number;
  slot_key: string;
  bus_address: string | null;
  module_template: { id: number; name: string; slug: string } | null;
  label: string;
  serial_number: string | null;
  metric_key_map: Record<string, string>;
  status: "active" | "inactive" | "removed";
  installed_at: string;
}

export interface ModuleCreatePayload {
  slot_key: string;
  bus_address?: string;
  module_template_id?: number;
  label: string;
  serial_number?: string;
  metric_key_map?: Record<string, string>;
}

export interface ModuleUpdatePayload {
  label?: string;
  serial_number?: string;
  metric_key_map?: Record<string, string>;
  status?: string;
}

// ─── Device Sensor Types (restructured) ────────────────

export interface DeviceSensor {
  id: number;
  device_id: string;
  metric_key: string;
  display_name: string;
  template_metric: { id: number; metric_key: string; display_name: string } | null;
  module: { id: number; label: string } | null;
  unit: string | null;
  min_range: number | null;
  max_range: number | null;
  precision_digits: number;
  status: "active" | "inactive" | "error";
  source: "required" | "optional" | "unmodeled";
  last_value: number | null;
  last_value_text: string | null;
  last_seen_at: string | null;
}

export interface DeviceSensorCreate {
  metric_key: string;
  display_name: string;
  template_metric_id?: number;
  device_module_id?: number;
  unit?: string;
  min_range?: number;
  max_range?: number;
  precision_digits?: number;
}

export interface DeviceSensorUpdate {
  display_name?: string;
  unit?: string;
  min_range?: number;
  max_range?: number;
  precision_digits?: number;
  status?: string;
}

// ─── Device Transport Types ────────────────────────────

export interface DeviceTransport {
  id: number;
  device_id: string;
  ingestion_protocol: string;
  physical_connectivity: string | null;
  protocol_config: Record<string, unknown>;
  connectivity_config: Record<string, unknown>;
  carrier_integration: { id: number; display_name: string } | null;
  is_primary: boolean;
  status: "active" | "inactive" | "failover";
  last_connected_at: string | null;
}

export interface TransportCreatePayload {
  ingestion_protocol: string;
  physical_connectivity?: string;
  protocol_config?: Record<string, unknown>;
  connectivity_config?: Record<string, unknown>;
  carrier_integration_id?: number;
  is_primary?: boolean;
}

export interface TransportUpdatePayload {
  physical_connectivity?: string;
  protocol_config?: Record<string, unknown>;
  connectivity_config?: Record<string, unknown>;
  carrier_integration_id?: number;
  is_primary?: boolean;
  status?: string;
}
```

### Update Existing Device Type

Update the `Device` interface (or `DeviceDetailResponse`) to include template info:

```typescript
// Add to existing Device interface:
template_id: number | null;
template: { id: number; name: string; slug: string; category: string } | null;
parent_device_id: string | null;
module_count: number;
sensor_count: number;
```

## Modify file: `frontend/src/services/api/devices.ts`

Add new API functions for modules and transports:

```typescript
// ─── Device Modules ────────────────────────────────────

export async function listDeviceModules(deviceId: string): Promise<DeviceModule[]> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/modules`);
}

export async function createDeviceModule(deviceId: string, data: ModuleCreatePayload): Promise<DeviceModule> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/modules`, data);
}

export async function updateDeviceModule(deviceId: string, moduleId: number, data: ModuleUpdatePayload): Promise<DeviceModule> {
  return apiPut(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/modules/${moduleId}`, data);
}

export async function deleteDeviceModule(deviceId: string, moduleId: number): Promise<void> {
  return apiDelete(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/modules/${moduleId}`);
}

// ─── Device Transports ─────────────────────────────────

export async function listDeviceTransports(deviceId: string): Promise<DeviceTransport[]> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/transports`);
}

export async function createDeviceTransport(deviceId: string, data: TransportCreatePayload): Promise<DeviceTransport> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/transports`, data);
}

export async function updateDeviceTransport(deviceId: string, transportId: number, data: TransportUpdatePayload): Promise<DeviceTransport> {
  return apiPut(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/transports/${transportId}`, data);
}

export async function deleteDeviceTransport(deviceId: string, transportId: number): Promise<void> {
  return apiDelete(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/transports/${transportId}`);
}
```

## Modify file: `frontend/src/services/api/sensors.ts`

Update the sensor functions to use the new `device_sensors` endpoints (the paths are the same but the response shapes changed). Update the type imports to use `DeviceSensor`, `DeviceSensorCreate`, `DeviceSensorUpdate` instead of the old types.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

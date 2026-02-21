# Task 001 — Carrier API Functions & Types

## Files

1. Create `frontend/src/services/api/carrier.ts`
2. Update `frontend/src/services/api/types.ts`

## Types (add to `types.ts`)

```typescript
// ─── Carrier Integration Types ───────────────────────

export interface CarrierIntegration {
  id: number;
  carrier_name: string;
  display_name: string;
  enabled: boolean;
  account_id: string | null;
  api_key_masked: string | null;     // Last 4 chars only
  sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  last_sync_status: string;          // 'success', 'error', 'partial', 'never'
  last_sync_error: string | null;
  created_at: string;
}

export interface CarrierIntegrationCreate {
  carrier_name: string;
  display_name: string;
  api_key: string;
  api_secret?: string;
  account_id?: string;
  api_base_url?: string;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  config?: Record<string, unknown>;
}

export interface CarrierIntegrationUpdate {
  display_name?: string;
  api_key?: string;
  api_secret?: string;
  account_id?: string;
  api_base_url?: string;
  enabled?: boolean;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  config?: Record<string, unknown>;
}

export interface CarrierDeviceStatus {
  linked: boolean;
  carrier_name?: string;
  device_info?: {
    carrier_device_id: string;
    iccid: string | null;
    sim_status: string | null;
    network_status: string | null;
    ip_address: string | null;
    network_type: string | null;
    last_connection: string | null;
    signal_strength: number | null;
  };
}

export interface CarrierDeviceUsage {
  linked: boolean;
  carrier_name?: string;
  usage?: {
    data_used_bytes: number;
    data_limit_bytes: number | null;
    data_used_mb: number;
    data_limit_mb: number | null;
    usage_pct: number;
    billing_cycle_start: string | null;
    billing_cycle_end: string | null;
    sms_count: number;
  };
}

export interface CarrierActionResult {
  action: string;
  success: boolean;
  carrier_name: string;
}

export interface CarrierLinkRequest {
  carrier_integration_id: number;
  carrier_device_id: string;
}
```

## API Functions (new `carrier.ts`)

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import type {
  CarrierIntegration,
  CarrierIntegrationCreate,
  CarrierIntegrationUpdate,
  CarrierDeviceStatus,
  CarrierDeviceUsage,
  CarrierActionResult,
  CarrierLinkRequest,
} from "./types";

// ─── Carrier Integrations ────────────────────────────

export async function listCarrierIntegrations(): Promise<{ integrations: CarrierIntegration[] }> {
  return apiGet("/api/v1/customer/carrier/integrations");
}

export async function createCarrierIntegration(data: CarrierIntegrationCreate): Promise<CarrierIntegration> {
  return apiPost("/api/v1/customer/carrier/integrations", data);
}

export async function updateCarrierIntegration(id: number, data: CarrierIntegrationUpdate): Promise<CarrierIntegration> {
  return apiPut(`/api/v1/customer/carrier/integrations/${id}`, data);
}

export async function deleteCarrierIntegration(id: number): Promise<void> {
  return apiDelete(`/api/v1/customer/carrier/integrations/${id}`);
}

// ─── Device Carrier Operations ───────────────────────

export async function getCarrierStatus(deviceId: string): Promise<CarrierDeviceStatus> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/status`);
}

export async function getCarrierUsage(deviceId: string): Promise<CarrierDeviceUsage> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/usage`);
}

export async function getCarrierDiagnostics(deviceId: string): Promise<Record<string, unknown>> {
  return apiGet(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/diagnostics`);
}

export async function executeCarrierAction(
  deviceId: string,
  action: "activate" | "suspend" | "deactivate" | "reboot",
): Promise<CarrierActionResult> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/actions/${action}`, {});
}

export async function linkDeviceToCarrier(deviceId: string, data: CarrierLinkRequest): Promise<void> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/link`, data);
}
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

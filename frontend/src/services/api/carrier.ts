import { apiDelete, apiGet, apiPost, apiPut } from "./client";
import type {
  CarrierIntegration,
  CarrierIntegrationCreate,
  CarrierIntegrationUpdate,
  CarrierDeviceStatus,
  CarrierDeviceUsage,
  CarrierActionResult,
  CarrierLinkRequest,
  CarrierProvisionRequest,
  CarrierProvisionResponse,
  CarrierPlansResponse,
} from "./types";

// ─── Carrier Integrations ────────────────────────────

export async function listCarrierIntegrations(): Promise<{ integrations: CarrierIntegration[] }> {
  return apiGet("/api/v1/customer/carrier/integrations");
}

export async function createCarrierIntegration(data: CarrierIntegrationCreate): Promise<CarrierIntegration> {
  return apiPost("/api/v1/customer/carrier/integrations", data);
}

export async function updateCarrierIntegration(
  id: number,
  data: CarrierIntegrationUpdate,
): Promise<CarrierIntegration> {
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
  return apiPost(
    `/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/actions/${action}`,
    {},
  );
}

export async function linkDeviceToCarrier(deviceId: string, data: CarrierLinkRequest): Promise<void> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/link`, data);
}

export async function provisionDeviceSim(
  deviceId: string,
  data: CarrierProvisionRequest,
): Promise<CarrierProvisionResponse> {
  return apiPost(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/provision`, data);
}

export async function listCarrierPlans(integrationId: number): Promise<CarrierPlansResponse> {
  return apiGet(`/api/v1/customer/carrier/integrations/${integrationId}/plans`);
}


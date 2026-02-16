import { apiGet, apiPost } from "./client";

// ── Types ────────────────────────────────────────────────────────

export type CampaignStatus =
  | "CREATED"
  | "RUNNING"
  | "PAUSED"
  | "COMPLETED"
  | "ABORTED";
export type DeviceOtaStatus =
  | "PENDING"
  | "DOWNLOADING"
  | "INSTALLING"
  | "SUCCESS"
  | "FAILED"
  | "SKIPPED";

export interface FirmwareVersion {
  id: number;
  version: string;
  description: string | null;
  file_url: string;
  file_size_bytes: number | null;
  checksum_sha256: string | null;
  device_type: string | null;
  created_at: string;
  created_by: string | null;
}

export interface OtaCampaign {
  id: number;
  name: string;
  status: CampaignStatus;
  rollout_strategy: string;
  rollout_rate: number;
  abort_threshold: number;
  total_devices: number;
  succeeded: number;
  failed: number;
  target_group_id: string;
  firmware_version: string;
  firmware_device_type: string | null;
  firmware_url?: string;
  firmware_checksum?: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  created_by: string | null;
  status_breakdown?: Record<string, number>;
}

export interface OtaDeviceStatus {
  device_id: string;
  status: DeviceOtaStatus;
  progress_pct: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface CreateFirmwarePayload {
  version: string;
  description?: string;
  file_url: string;
  file_size_bytes?: number;
  checksum_sha256?: string;
  device_type?: string;
}

export interface CreateCampaignPayload {
  name: string;
  firmware_version_id: number;
  target_group_id: string;
  rollout_strategy?: "linear" | "canary";
  rollout_rate?: number;
  abort_threshold?: number;
}

// ── Firmware API ─────────────────────────────────────────────────

export async function listFirmware(deviceType?: string): Promise<{
  firmware_versions: FirmwareVersion[];
  total: number;
}> {
  const params = deviceType ? `?device_type=${encodeURIComponent(deviceType)}` : "";
  return apiGet(`/api/v1/customer/firmware${params}`);
}

export async function createFirmware(
  payload: CreateFirmwarePayload
): Promise<FirmwareVersion> {
  return apiPost("/api/v1/customer/firmware", payload);
}

// ── Campaign API ─────────────────────────────────────────────────

export async function listCampaigns(status?: string): Promise<{
  campaigns: OtaCampaign[];
  total: number;
}> {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiGet(`/api/v1/customer/ota/campaigns${params}`);
}

export async function getCampaign(id: number): Promise<OtaCampaign> {
  return apiGet(`/api/v1/customer/ota/campaigns/${id}`);
}

export async function createCampaign(
  payload: CreateCampaignPayload
): Promise<OtaCampaign> {
  return apiPost("/api/v1/customer/ota/campaigns", payload);
}

export async function startCampaign(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`/api/v1/customer/ota/campaigns/${id}/start`, {});
}

export async function pauseCampaign(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`/api/v1/customer/ota/campaigns/${id}/pause`, {});
}

export async function abortCampaign(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`/api/v1/customer/ota/campaigns/${id}/abort`, {});
}

export async function listCampaignDevices(
  id: number,
  params?: { status?: string; limit?: number; offset?: number }
): Promise<{
  campaign_id: number;
  devices: OtaDeviceStatus[];
  total: number;
  limit: number;
  offset: number;
}> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiGet(`/api/v1/customer/ota/campaigns/${id}/devices${qs ? `?${qs}` : ""}`);
}


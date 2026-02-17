import keycloak from "@/services/auth/keycloak";
import { apiGet, apiPost, ApiError } from "./client";

// ---------- Types ----------

export interface DeviceCertificate {
  id: number;
  tenant_id: string;
  device_id: string;
  fingerprint_sha256: string;
  common_name: string;
  issuer: string;
  serial_number: string;
  status: "ACTIVE" | "REVOKED" | "EXPIRED";
  not_before: string;
  not_after: string;
  revoked_at: string | null;
  revoked_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificateListResponse {
  certificates: DeviceCertificate[];
  total: number;
  limit: number;
  offset: number;
}

export interface CertificateDetailResponse extends DeviceCertificate {
  cert_pem: string;
}

export interface GenerateCertResponse {
  certificate: DeviceCertificate;
  cert_pem: string;
  private_key_pem: string;
  ca_cert_pem: string;
  warning: string;
}

export interface RotateCertResponse {
  new_certificate: DeviceCertificate;
  cert_pem: string;
  private_key_pem: string;
  ca_cert_pem: string;
  old_certificates: Array<{
    id: number;
    fingerprint: string;
    status: string;
    scheduled_revoke_at: string;
  }>;
  grace_period_hours: number;
  warning: string;
}

export interface RevokeResponse {
  id: number;
  fingerprint_sha256: string;
  status: string;
  revoked_at: string;
}

// ---------- API Functions ----------

export async function listCertificates(params?: {
  device_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<CertificateListResponse> {
  const query = new URLSearchParams();
  if (params?.device_id) query.set("device_id", params.device_id);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiGet(`/api/v1/customer/certificates${qs ? `?${qs}` : ""}`);
}

export async function getCertificate(certId: number): Promise<CertificateDetailResponse> {
  return apiGet(`/api/v1/customer/certificates/${certId}`);
}

export async function generateCertificate(
  deviceId: string,
  validityDays = 365
): Promise<GenerateCertResponse> {
  return apiPost(`/api/v1/customer/devices/${deviceId}/certificates/generate`, {
    validity_days: validityDays,
  });
}

export async function rotateCertificate(
  deviceId: string,
  validityDays = 365,
  revokeOldAfterHours?: number
): Promise<RotateCertResponse> {
  return apiPost(`/api/v1/customer/devices/${deviceId}/certificates/rotate`, {
    validity_days: validityDays,
    revoke_old_after_hours: revokeOldAfterHours,
  });
}

export async function revokeCertificate(
  certId: number,
  reason = "manual_revocation"
): Promise<RevokeResponse> {
  return apiPost(`/api/v1/customer/certificates/${certId}/revoke`, { reason });
}

export async function downloadCaBundle(): Promise<string> {
  // Returns raw PEM text.
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch (error) {
      console.error("Auth token refresh failed:", error);
      keycloak.login();
      throw new ApiError(401, "Token expired");
    }
  }

  const headers: Record<string, string> = {};
  if (keycloak.token) headers["Authorization"] = `Bearer ${keycloak.token}`;

  const response = await fetch("/api/v1/customer/ca-bundle", { headers });
  if (!response.ok) throw new Error("Failed to download CA bundle");
  return response.text();
}

// ---------- Operator API (fleet-wide) ----------

export async function listAllCertificates(params?: {
  status?: string;
  tenant_id?: string;
  limit?: number;
  offset?: number;
}): Promise<CertificateListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.tenant_id) query.set("tenant_id", params.tenant_id);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiGet(`/api/v1/operator/certificates${qs ? `?${qs}` : ""}`);
}

export async function downloadOperatorCaBundle(): Promise<string> {
  // Returns raw PEM text.
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch (error) {
      console.error("Auth token refresh failed:", error);
      keycloak.login();
      throw new ApiError(401, "Token expired");
    }
  }

  const headers: Record<string, string> = {};
  if (keycloak.token) headers["Authorization"] = `Bearer ${keycloak.token}`;

  const response = await fetch("/api/v1/operator/ca-bundle", { headers });
  if (!response.ok) throw new Error("Failed to download CA bundle");
  return response.text();
}


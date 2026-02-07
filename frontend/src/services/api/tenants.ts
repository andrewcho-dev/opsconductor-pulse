import { apiGet, apiPost, apiPatch, apiDelete } from "./client";

export interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  contact_email?: string;
  contact_name?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TenantStats {
  tenant_id: string;
  name: string;
  status: string;
  stats: {
    devices: { total: number; active: number; online: number; stale: number };
    alerts: { open: number; closed: number; last_24h: number };
    integrations: { total: number; active: number };
    rules: { total: number; active: number };
    sites: number;
    last_device_activity: string | null;
    last_alert: string | null;
  };
}

export interface TenantSummary {
  tenant_id: string;
  name: string;
  status: string;
  device_count: number;
  online_count: number;
  open_alerts: number;
  last_activity: string | null;
  created_at: string;
}

export interface TenantCreate {
  tenant_id: string;
  name: string;
  contact_email?: string;
  contact_name?: string;
  metadata?: Record<string, unknown>;
}

export interface TenantUpdate {
  name?: string;
  contact_email?: string;
  contact_name?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export async function fetchTenants(
  status = "ACTIVE"
): Promise<{ tenants: Tenant[]; total: number }> {
  return apiGet(`/operator/tenants?status=${status}`);
}

export async function fetchTenantsSummary(): Promise<{ tenants: TenantSummary[] }> {
  return apiGet("/operator/tenants/stats/summary");
}

export async function fetchTenant(tenantId: string): Promise<Tenant> {
  return apiGet(`/operator/tenants/${tenantId}`);
}

export async function fetchTenantStats(tenantId: string): Promise<TenantStats> {
  return apiGet(`/operator/tenants/${tenantId}/stats`);
}

export async function createTenant(
  data: TenantCreate
): Promise<{ tenant_id: string }> {
  return apiPost("/operator/tenants", data);
}

export async function updateTenant(
  tenantId: string,
  data: TenantUpdate
): Promise<void> {
  await apiPatch(`/operator/tenants/${tenantId}`, data);
}

export async function deleteTenant(tenantId: string): Promise<void> {
  await apiDelete(`/operator/tenants/${tenantId}`);
}


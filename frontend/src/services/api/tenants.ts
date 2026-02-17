import { apiGet, apiPost, apiPatch, apiDelete } from "./client";

export interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  contact_email?: string;
  contact_name?: string;
  legal_name?: string;
  phone?: string;
  industry?: string;
  company_size?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  data_residency_region?: string;
  support_tier?: string;
  sla_level?: number;
  stripe_customer_id?: string;
  billing_email?: string;
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
  legal_name?: string;
  phone?: string;
  industry?: string;
  company_size?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  data_residency_region?: string;
  support_tier?: string;
  sla_level?: number;
  stripe_customer_id?: string;
  billing_email?: string;
  metadata?: Record<string, unknown>;
}

export interface TenantUpdate {
  name?: string;
  contact_email?: string;
  contact_name?: string;
  legal_name?: string;
  phone?: string;
  industry?: string;
  company_size?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  data_residency_region?: string;
  support_tier?: string;
  sla_level?: number;
  stripe_customer_id?: string;
  billing_email?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export async function fetchTenants(
  status = "ACTIVE"
): Promise<{ tenants: Tenant[]; total: number }> {
  return apiGet(`/api/v1/operator/tenants?status=${status}`);
}

export async function fetchTenantsSummary(): Promise<{ tenants: TenantSummary[] }> {
  return apiGet("/api/v1/operator/tenants/stats/summary");
}

export async function fetchTenant(tenantId: string): Promise<Tenant> {
  return apiGet(`/api/v1/operator/tenants/${tenantId}`);
}

export async function fetchTenantStats(tenantId: string): Promise<TenantStats> {
  return apiGet(`/api/v1/operator/tenants/${tenantId}/stats`);
}

export async function createTenant(
  data: TenantCreate
): Promise<{ tenant_id: string }> {
  return apiPost("/api/v1/operator/tenants", data);
}

export async function updateTenant(
  tenantId: string,
  data: TenantUpdate
): Promise<void> {
  await apiPatch(`/api/v1/operator/tenants/${tenantId}`, data);
}

export async function deleteTenant(tenantId: string): Promise<void> {
  await apiDelete(`/api/v1/operator/tenants/${tenantId}`);
}


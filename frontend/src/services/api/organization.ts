import { apiGet, apiPut } from "./client";

export interface OrganizationProfile {
  tenant_id: string;
  name: string;
  legal_name: string | null;
  contact_email: string | null;
  contact_name: string | null;
  phone: string | null;
  industry: string | null;
  company_size: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state_province: string | null;
  postal_code: string | null;
  country: string | null;
  data_residency_region: string | null;
  support_tier: string | null;
  sla_level: number | null;
  billing_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationUpdate {
  name?: string;
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
  billing_email?: string;
}

export async function getOrganization(): Promise<OrganizationProfile> {
  return apiGet("/api/v1/customer/organization");
}

export async function updateOrganization(
  data: OrganizationUpdate
): Promise<OrganizationProfile> {
  return apiPut("/api/v1/customer/organization", data);
}


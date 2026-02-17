import { apiGet, apiPost, apiPut } from "./client";

export interface OperatorDeviceTier {
  tier_id: number;
  name: string;
  display_name: string;
  description: string;
  features: Record<string, boolean>;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export async function fetchDeviceTiers(): Promise<{ tiers: OperatorDeviceTier[] }> {
  return apiGet("/api/v1/operator/device-tiers");
}

export async function createDeviceTier(data: {
  name: string;
  display_name: string;
  description?: string;
  features: Record<string, boolean>;
  sort_order: number;
}): Promise<OperatorDeviceTier> {
  return apiPost("/api/v1/operator/device-tiers", data);
}

export async function updateDeviceTier(
  tierId: number,
  data: {
    display_name?: string;
    description?: string;
    features?: Record<string, boolean>;
    sort_order?: number;
    is_active?: boolean;
  }
): Promise<OperatorDeviceTier> {
  return apiPut(`/api/v1/operator/device-tiers/${tierId}`, data);
}


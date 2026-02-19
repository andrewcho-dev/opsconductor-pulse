import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface OperatorDevicePlan {
  plan_id: string;
  name: string;
  description: string;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  monthly_price_cents: number;
  annual_price_cents: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export async function fetchDevicePlans(): Promise<{ plans: OperatorDevicePlan[] }> {
  return apiGet("/api/v1/operator/device-plans");
}

export async function createDevicePlan(data: {
  plan_id: string;
  name: string;
  description?: string;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  monthly_price_cents: number;
  annual_price_cents: number;
  sort_order: number;
}): Promise<OperatorDevicePlan> {
  return apiPost("/api/v1/operator/device-plans", data);
}

export async function updateDevicePlan(
  planId: string,
  data: {
    name?: string;
    description?: string;
    limits?: Record<string, number>;
    features?: Record<string, boolean>;
    monthly_price_cents?: number;
    annual_price_cents?: number;
    sort_order?: number;
    is_active?: boolean;
  }
): Promise<OperatorDevicePlan> {
  return apiPut(`/api/v1/operator/device-plans/${encodeURIComponent(planId)}`, data);
}

export async function deactivateDevicePlan(planId: string): Promise<void> {
  await apiDelete(`/api/v1/operator/device-plans/${encodeURIComponent(planId)}`);
}


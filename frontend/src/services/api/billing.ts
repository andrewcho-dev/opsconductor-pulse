import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface BillingConfig {
  stripe_configured: boolean;
  publishable_key: string | null;
}

export interface TierAllocation {
  subscription_id: string;
  tier_id: number;
  tier_name: string;
  tier_display_name: string;
  slot_limit: number;
  slots_used: number;
  slots_available: number;
}

export interface SubscriptionInfo {
  subscription_id: string;
  subscription_type: string;
  plan_id: string | null;
  status: string;
  device_limit: number;
  active_device_count: number;
  stripe_subscription_id: string | null;
  parent_subscription_id: string | null;
  description: string | null;
  term_start: string | null;
  term_end: string | null;
  grace_end?: string | null;
  is_stripe_managed?: boolean;
}

export interface BillingStatus {
  has_billing_account: boolean;
  billing_email: string | null;
  support_tier: string | null;
  sla_level: number | null;
  subscriptions: SubscriptionInfo[];
  tier_allocations: TierAllocation[];
}

export interface EntitlementInfo {
  current: number;
  limit: number;
}

export interface PlanUsage {
  plan_id: string | null;
  usage: {
    alert_rules: EntitlementInfo;
    notification_channels: EntitlementInfo;
    users: EntitlementInfo;
    devices: { current: number; limit: number | null };
  };
}

export interface DeviceTier {
  tier_id: number;
  name: string;
  display_name: string;
  description: string;
  features: Record<string, boolean>;
}

export async function getBillingConfig(): Promise<BillingConfig> {
  return apiGet("/api/v1/customer/billing/config");
}

export async function getBillingStatus(): Promise<BillingStatus> {
  return apiGet("/api/v1/customer/billing/status");
}

export async function getEntitlements(): Promise<PlanUsage> {
  return apiGet("/api/v1/customer/billing/entitlements");
}

export async function createCheckoutSession(data: {
  price_id: string;
  success_url: string;
  cancel_url: string;
}): Promise<{ url: string }> {
  return apiPost("/api/v1/customer/billing/checkout-session", data);
}

export async function createPortalSession(data: {
  return_url: string;
}): Promise<{ url: string }> {
  return apiPost("/api/v1/customer/billing/portal-session", data);
}

export async function createAddonCheckoutSession(data: {
  parent_subscription_id: string;
  price_id: string;
  success_url: string;
  cancel_url: string;
}): Promise<{ url: string; co_terminate_at: string }> {
  return apiPost("/api/v1/customer/billing/addon-checkout", data);
}

export async function getDeviceTiers(): Promise<DeviceTier[]> {
  const response = await apiGet<{ tiers: DeviceTier[] }>(
    "/api/v1/customer/device-tiers"
  );
  return response.tiers;
}

export async function assignDeviceTier(
  deviceId: string,
  tierId: number
): Promise<void> {
  await apiPut(`/api/v1/customer/devices/${deviceId}/tier`, { tier_id: tierId });
}

export async function removeDeviceTier(deviceId: string): Promise<void> {
  await apiDelete(`/api/v1/customer/devices/${deviceId}/tier`);
}


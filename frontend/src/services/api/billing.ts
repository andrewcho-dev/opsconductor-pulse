import { apiGet, apiPost } from "./client";
import type {
  AccountEntitlements,
  AccountTier,
  DevicePlan,
  DeviceSubscription,
} from "./types";

export interface BillingConfig {
  stripe_configured: boolean;
  publishable_key: string | null;
}

export interface BillingStatus {
  has_billing_account: boolean;
  billing_email: string | null;
  account_tier: {
    tier_id: string | null;
    name: string | null;
    monthly_price_cents: number;
  };
  device_plans: Array<{
    plan_id: string;
    plan_name: string;
    device_count: number;
    monthly_price_cents: number;
    total_monthly_price_cents: number;
  }>;
  total_monthly_price_cents: number;
}


export async function getBillingConfig(): Promise<BillingConfig> {
  return apiGet("/api/v1/customer/billing/config");
}

export async function getBillingStatus(): Promise<BillingStatus> {
  return apiGet("/api/v1/customer/billing/status");
}

export async function getEntitlements(): Promise<AccountEntitlements> {
  return apiGet("/api/v1/customer/billing/entitlements");
}

export async function listAccountTiers(): Promise<{ tiers: AccountTier[] }> {
  return apiGet("/api/v1/customer/billing/account-tiers");
}

export async function listDevicePlans(): Promise<{ plans: DevicePlan[] }> {
  return apiGet("/api/v1/customer/billing/device-plans");
}

export async function listDeviceSubscriptions(): Promise<{
  subscriptions: DeviceSubscription[];
}> {
  return apiGet("/api/v1/customer/billing/subscriptions");
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


import { apiGet } from "./client";

export interface SubscriptionStatus {
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  days_until_expiry: number | null;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED";
  subscription_count: number;
}

export async function getSubscription(): Promise<SubscriptionStatus> {
  const response = await apiGet<{
    subscriptions: { status: SubscriptionStatus["status"]; term_end: string | null }[];
    summary: {
      total_device_limit: number;
      total_active_devices: number;
      total_available: number;
    };
  }>("/customer/subscriptions");

  const statuses = response.subscriptions.map((sub) => sub.status);
  let status: SubscriptionStatus["status"] = "ACTIVE";
  if (statuses.includes("SUSPENDED")) {
    status = "SUSPENDED";
  } else if (statuses.includes("GRACE")) {
    status = "GRACE";
  } else if (statuses.includes("TRIAL") && !statuses.includes("ACTIVE")) {
    status = "TRIAL";
  }

  const activeTerms = response.subscriptions
    .filter((sub) => sub.status === "ACTIVE" && sub.term_end)
    .map((sub) => new Date(sub.term_end as string));
  const earliestExpiry = activeTerms.length
    ? new Date(Math.min(...activeTerms.map((d) => d.getTime())))
    : null;
  const days_until_expiry = earliestExpiry
    ? Math.max(
        0,
        Math.ceil((earliestExpiry.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
      )
    : null;

  return {
    device_limit: response.summary.total_device_limit,
    active_device_count: response.summary.total_active_devices,
    devices_available: response.summary.total_available,
    days_until_expiry,
    status,
    subscription_count: response.subscriptions.length,
  };
}

export interface SubscriptionAuditEvent {
  id: number;
  event_type: string;
  event_timestamp: string;
  actor_type: string | null;
  actor_id: string | null;
  details: Record<string, unknown> | null;
}

export async function getSubscriptionAudit(
  limit = 50,
  offset = 0
): Promise<{ events: SubscriptionAuditEvent[]; total: number }> {
  return apiGet(`/customer/subscription/audit?limit=${limit}&offset=${offset}`);
}

import { apiGet } from "./client";

export interface SubscriptionStatus {
  total_subscriptions: number;
  active_subscriptions: number;
  worst_status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED" | "CANCELLED";
  earliest_expiry_days: number | null;
}

export async function getSubscription(): Promise<SubscriptionStatus> {
  const response = await apiGet<{
    subscriptions: {
      subscription_id: string;
      device_id: string;
      plan_id: string;
      status: string;
      term_end: string | null;
    }[];
    summary: {
      total_subscriptions: number;
      active_subscriptions: number;
    };
  }>("/api/v1/customer/subscriptions");

  const statuses = response.subscriptions.map((s) => s.status);
  let worst_status: SubscriptionStatus["worst_status"] = "ACTIVE";
  if (statuses.includes("SUSPENDED")) worst_status = "SUSPENDED";
  else if (statuses.includes("GRACE")) worst_status = "GRACE";
  else if (statuses.includes("TRIAL") && !statuses.includes("ACTIVE")) worst_status = "TRIAL";

  const activeTerms = response.subscriptions
    .filter((s) => s.status === "ACTIVE" && s.term_end)
    .map((s) => new Date(s.term_end as string));
  const earliestExpiry = activeTerms.length
    ? new Date(Math.min(...activeTerms.map((d) => d.getTime())))
    : null;
  const earliest_expiry_days = earliestExpiry
    ? Math.max(0, Math.ceil((earliestExpiry.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : null;

  return {
    total_subscriptions: response.summary.total_subscriptions,
    active_subscriptions: response.summary.active_subscriptions,
    worst_status,
    earliest_expiry_days,
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
  return apiGet(`/api/v1/customer/subscription/audit?limit=${limit}&offset=${offset}`);
}

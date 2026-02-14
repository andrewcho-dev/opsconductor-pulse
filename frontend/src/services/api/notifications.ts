import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export type ChannelType = "slack" | "pagerduty" | "teams" | "webhook";

export interface NotificationChannel {
  channel_id: number;
  name: string;
  channel_type: ChannelType;
  config: Record<string, string>;
  is_enabled: boolean;
  created_at: string;
}

export interface RoutingRule {
  rule_id: number;
  channel_id: number;
  min_severity?: number;
  alert_type?: string;
  device_tag_key?: string;
  device_tag_val?: string;
  throttle_minutes: number;
  is_enabled: boolean;
}

export async function listChannels(): Promise<{ channels: NotificationChannel[] }> {
  return apiGet("/customer/notification-channels");
}

export async function createChannel(
  body: Omit<NotificationChannel, "channel_id" | "created_at">
): Promise<NotificationChannel> {
  return apiPost("/customer/notification-channels", body);
}

export async function updateChannel(
  id: number,
  body: Partial<NotificationChannel>
): Promise<NotificationChannel> {
  return apiPut(`/customer/notification-channels/${id}`, body);
}

export async function deleteChannel(id: number): Promise<void> {
  await apiDelete(`/customer/notification-channels/${id}`);
}

export async function testChannel(id: number): Promise<{ ok: boolean; error?: string }> {
  return apiPost(`/customer/notification-channels/${id}/test`, {});
}

export async function listRoutingRules(): Promise<{ rules: RoutingRule[] }> {
  return apiGet("/customer/notification-routing-rules");
}

export async function createRoutingRule(body: Omit<RoutingRule, "rule_id">): Promise<RoutingRule> {
  return apiPost("/customer/notification-routing-rules", body);
}

export async function updateRoutingRule(id: number, body: Partial<RoutingRule>): Promise<RoutingRule> {
  return apiPut(`/customer/notification-routing-rules/${id}`, body);
}

export async function deleteRoutingRule(id: number): Promise<void> {
  await apiDelete(`/customer/notification-routing-rules/${id}`);
}

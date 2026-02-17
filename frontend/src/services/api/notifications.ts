import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export type ChannelType = "slack" | "pagerduty" | "teams" | "webhook" | "http" | "email" | "snmp" | "mqtt";

export interface NotificationChannel {
  channel_id: number;
  name: string;
  channel_type: ChannelType;
  config: Record<string, unknown>;
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
  site_ids?: string[];
  device_prefixes?: string[];
  deliver_on?: string[];
  priority?: number;
  throttle_minutes: number;
  is_enabled: boolean;
}

export async function listChannels(): Promise<{ channels: NotificationChannel[] }> {
  return apiGet("/api/v1/customer/notification-channels");
}

export async function createChannel(
  body: Omit<NotificationChannel, "channel_id" | "created_at">
): Promise<NotificationChannel> {
  return apiPost("/api/v1/customer/notification-channels", body);
}

export async function updateChannel(
  id: number,
  body: Partial<NotificationChannel>
): Promise<NotificationChannel> {
  return apiPut(`/api/v1/customer/notification-channels/${id}`, body);
}

export async function deleteChannel(id: number): Promise<void> {
  await apiDelete(`/api/v1/customer/notification-channels/${id}`);
}

export async function testChannel(id: number): Promise<{ status?: string; ok?: boolean; message?: string; error?: string }> {
  return apiPost(`/api/v1/customer/notification-channels/${id}/test`, {});
}

export async function listRoutingRules(): Promise<{ rules: RoutingRule[] }> {
  return apiGet("/api/v1/customer/notification-routing-rules");
}

export async function createRoutingRule(body: Omit<RoutingRule, "rule_id">): Promise<RoutingRule> {
  return apiPost("/api/v1/customer/notification-routing-rules", body);
}

export async function updateRoutingRule(id: number, body: Partial<RoutingRule>): Promise<RoutingRule> {
  return apiPut(`/api/v1/customer/notification-routing-rules/${id}`, body);
}

export async function deleteRoutingRule(id: number): Promise<void> {
  await apiDelete(`/api/v1/customer/notification-routing-rules/${id}`);
}

export interface NotificationJob {
  job_id: number;
  channel_id: number;
  alert_id: number;
  status: string;
  attempts: number;
  deliver_on_event: string;
  last_error?: string;
  created_at: string;
}

export async function listNotificationJobs(
  channelId?: number,
  status?: string,
  limit = 20
): Promise<{ jobs: NotificationJob[] }> {
  const params = new URLSearchParams();
  if (channelId) params.set("channel_id", String(channelId));
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  return apiGet(`/api/v1/customer/notification-jobs?${params.toString()}`);
}

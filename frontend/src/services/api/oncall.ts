import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface OncallLayer {
  layer_id?: number;
  name: string;
  rotation_type: "daily" | "weekly" | "custom";
  shift_duration_hours: number;
  handoff_day: number;
  handoff_hour: number;
  responders: string[];
  layer_order: number;
}

export interface OncallSchedule {
  schedule_id: number;
  name: string;
  description?: string;
  timezone: string;
  layers: OncallLayer[];
  created_at: string;
}

export interface OncallOverride {
  override_id: number;
  layer_id?: number;
  responder: string;
  start_at: string;
  end_at: string;
  reason?: string;
}

export interface TimelineSlot {
  start: string;
  end: string;
  responder: string;
  layer_name: string;
  is_override: boolean;
}

export interface CurrentOncall {
  responder: string;
  layer: string;
  until: string;
}

export async function listSchedules(): Promise<{ schedules: OncallSchedule[] }> {
  return apiGet("/customer/oncall-schedules");
}
export async function createSchedule(body: Partial<OncallSchedule>): Promise<OncallSchedule> {
  return apiPost("/customer/oncall-schedules", body);
}
export async function updateSchedule(id: number, body: Partial<OncallSchedule>): Promise<OncallSchedule> {
  return apiPut(`/customer/oncall-schedules/${id}`, body);
}
export async function deleteSchedule(id: number): Promise<void> {
  await apiDelete(`/customer/oncall-schedules/${id}`);
}
export async function getCurrentOncall(scheduleId: number): Promise<CurrentOncall> {
  return apiGet(`/customer/oncall-schedules/${scheduleId}/current`);
}
export async function getTimeline(
  scheduleId: number,
  days = 14
): Promise<{ slots: TimelineSlot[] }> {
  return apiGet(`/customer/oncall-schedules/${scheduleId}/timeline?days=${days}`);
}
export async function listOverrides(scheduleId: number): Promise<{ overrides: OncallOverride[] }> {
  return apiGet(`/customer/oncall-schedules/${scheduleId}/overrides`);
}
export async function createOverride(
  scheduleId: number,
  body: Omit<OncallOverride, "override_id">
): Promise<OncallOverride> {
  return apiPost(`/customer/oncall-schedules/${scheduleId}/overrides`, body);
}
export async function deleteOverride(scheduleId: number, overrideId: number): Promise<void> {
  await apiDelete(`/customer/oncall-schedules/${scheduleId}/overrides/${overrideId}`);
}

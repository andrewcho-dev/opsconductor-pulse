import { apiGet, apiPut } from "./client";

export interface UserPreferences {
  tenant_id: string;
  user_id: string;
  display_name: string | null;
  timezone: string;
  notification_prefs: {
    email_digest_frequency?: "daily" | "weekly" | "disabled";
    [key: string]: unknown;
  };
  created_at: string | null;
  updated_at: string | null;
}

export interface UpdatePreferencesPayload {
  display_name?: string | null;
  timezone?: string;
  notification_prefs?: Record<string, unknown>;
}

export async function fetchPreferences(): Promise<UserPreferences> {
  return apiGet("/api/v1/customer/preferences");
}

export async function updatePreferences(
  payload: UpdatePreferencesPayload
): Promise<UserPreferences & { message: string }> {
  return apiPut("/api/v1/customer/preferences", payload);
}

export const TIMEZONE_OPTIONS = [
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
  { value: "America/New_York", label: "Eastern Time (New York)" },
  { value: "America/Chicago", label: "Central Time (Chicago)" },
  { value: "America/Denver", label: "Mountain Time (Denver)" },
  { value: "America/Los_Angeles", label: "Pacific Time (Los Angeles)" },
  { value: "America/Toronto", label: "Eastern Time (Toronto)" },
  { value: "America/Vancouver", label: "Pacific Time (Vancouver)" },
  { value: "America/Sao_Paulo", label: "Brasilia Time (Sao Paulo)" },
  { value: "America/Mexico_City", label: "Central Time (Mexico City)" },
  { value: "Europe/London", label: "GMT (London)" },
  { value: "Europe/Berlin", label: "CET (Berlin)" },
  { value: "Europe/Paris", label: "CET (Paris)" },
  { value: "Europe/Madrid", label: "CET (Madrid)" },
  { value: "Europe/Rome", label: "CET (Rome)" },
  { value: "Europe/Amsterdam", label: "CET (Amsterdam)" },
  { value: "Europe/Stockholm", label: "CET (Stockholm)" },
  { value: "Europe/Warsaw", label: "CET (Warsaw)" },
  { value: "Europe/Moscow", label: "MSK (Moscow)" },
  { value: "Asia/Tokyo", label: "JST (Tokyo)" },
  { value: "Asia/Shanghai", label: "CST (Shanghai)" },
  { value: "Asia/Hong_Kong", label: "HKT (Hong Kong)" },
  { value: "Asia/Singapore", label: "SGT (Singapore)" },
  { value: "Asia/Seoul", label: "KST (Seoul)" },
  { value: "Asia/Kolkata", label: "IST (Kolkata)" },
  { value: "Asia/Dubai", label: "GST (Dubai)" },
  { value: "Asia/Bangkok", label: "ICT (Bangkok)" },
  { value: "Australia/Sydney", label: "AEST (Sydney)" },
  { value: "Australia/Melbourne", label: "AEST (Melbourne)" },
  { value: "Australia/Perth", label: "AWST (Perth)" },
  { value: "Pacific/Auckland", label: "NZST (Auckland)" },
  { value: "Pacific/Honolulu", label: "HST (Honolulu)" },
  { value: "Africa/Cairo", label: "EET (Cairo)" },
  { value: "Africa/Johannesburg", label: "SAST (Johannesburg)" },
  { value: "Africa/Lagos", label: "WAT (Lagos)" },
] as const;


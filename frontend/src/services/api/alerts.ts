import { apiGet } from "./client";
import type { AlertListResponse, AlertDetailResponse } from "./types";

export async function fetchAlerts(
  status = "OPEN",
  limit = 100,
  offset = 0,
  alertType?: string
): Promise<AlertListResponse> {
  let url = `/api/v2/alerts?status=${status}&limit=${limit}&offset=${offset}`;
  if (alertType) url += `&alert_type=${encodeURIComponent(alertType)}`;
  return apiGet(url);
}

export async function fetchAlert(
  alertId: number
): Promise<AlertDetailResponse> {
  return apiGet(`/api/v2/alerts/${alertId}`);
}

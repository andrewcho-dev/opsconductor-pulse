import { apiGet } from "./client";

export interface DeliveryJob {
  job_id: number;
  alert_id: number;
  integration_id: string;
  route_id: string;
  status: string;
  attempts: number;
  last_error: string | null;
  deliver_on_event: string;
  created_at: string;
  updated_at: string;
}

export interface DeliveryAttempt {
  attempt_no: number;
  ok: boolean;
  http_status: number | null;
  latency_ms: number | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

export async function fetchDeliveryJobs(params: {
  status?: string;
  integration_id?: string;
  limit?: number;
  offset?: number;
}): Promise<{ jobs: DeliveryJob[]; total: number }> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.integration_id) qs.set("integration_id", params.integration_id);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.offset) qs.set("offset", String(params.offset));
  return apiGet(`/api/v1/customer/delivery-jobs?${qs.toString()}`);
}

export async function fetchDeliveryJobAttempts(
  jobId: number
): Promise<{ job_id: number; attempts: DeliveryAttempt[] }> {
  return apiGet(`/api/v1/customer/delivery-jobs/${jobId}/attempts`);
}

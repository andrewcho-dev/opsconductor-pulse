import { apiDelete, apiGet, apiPost } from "./client";

export type JobStatus = "IN_PROGRESS" | "COMPLETED" | "CANCELED" | "DELETION_IN_PROGRESS";
export type ExecutionStatus =
  | "QUEUED"
  | "IN_PROGRESS"
  | "SUCCEEDED"
  | "FAILED"
  | "TIMED_OUT"
  | "REJECTED";

export interface JobExecution {
  device_id: string;
  status: ExecutionStatus;
  status_details: Record<string, unknown> | null;
  queued_at: string;
  started_at: string | null;
  last_updated_at: string;
  execution_number: number;
}

export interface Job {
  job_id: string;
  document_type: string;
  document_params: Record<string, unknown>;
  status: JobStatus;
  target_device_id: string | null;
  target_group_id: string | null;
  target_all: boolean;
  expires_at: string | null;
  created_by: string | null;
  created_at: string;
  total_executions?: number;
  succeeded_count?: number;
  failed_count?: number;
  executions?: JobExecution[];
}

export interface CreateJobPayload {
  document_type: string;
  document_params: Record<string, unknown>;
  target_device_id?: string;
  target_group_id?: string;
  target_all?: boolean;
  expires_in_hours?: number;
}

export async function listJobs(status?: string): Promise<Job[]> {
  const url = status ? `/customer/jobs?status=${encodeURIComponent(status)}` : "/customer/jobs";
  return apiGet(url);
}

export async function getJob(jobId: string): Promise<Job> {
  return apiGet(`/customer/jobs/${encodeURIComponent(jobId)}`);
}

export async function createJob(payload: CreateJobPayload): Promise<{ job_id: string }> {
  return apiPost("/customer/jobs", payload);
}

export async function cancelJob(jobId: string): Promise<void> {
  await apiDelete(`/customer/jobs/${encodeURIComponent(jobId)}`);
}

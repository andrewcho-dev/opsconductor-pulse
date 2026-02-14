import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface EscalationLevel {
  level_id?: number;
  level_number: number;
  delay_minutes: number;
  notify_email?: string;
  notify_webhook?: string;
  oncall_schedule_id?: number;
}

export interface EscalationPolicy {
  policy_id: number;
  tenant_id: string;
  name: string;
  description?: string;
  is_default: boolean;
  levels: EscalationLevel[];
  created_at: string;
  updated_at: string;
}

export type EscalationPolicyCreateBody = Omit<
  EscalationPolicy,
  "policy_id" | "tenant_id" | "created_at" | "updated_at"
>;

export async function listEscalationPolicies(): Promise<{ policies: EscalationPolicy[] }> {
  return apiGet("/customer/escalation-policies");
}

export async function createEscalationPolicy(
  body: EscalationPolicyCreateBody
): Promise<EscalationPolicy> {
  return apiPost("/customer/escalation-policies", body);
}

export async function updateEscalationPolicy(
  id: number,
  body: Partial<EscalationPolicy>
): Promise<EscalationPolicy> {
  return apiPut(`/customer/escalation-policies/${id}`, body);
}

export async function deleteEscalationPolicy(id: number): Promise<void> {
  await apiDelete(`/customer/escalation-policies/${id}`);
}

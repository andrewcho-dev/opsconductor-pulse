import { apiGet } from "./client";

export interface AuditLogEvent {
  timestamp: string;
  event_type: string;
  category: string;
  severity: string;
  entity_type: string | null;
  entity_id: string | null;
  entity_name: string | null;
  action: string;
  message: string;
  details: Record<string, unknown> | null;
  source_service: string;
  actor_type: string | null;
  actor_id: string | null;
  actor_name: string | null;
}

export interface AuditLogResponse {
  events: AuditLogEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditLogFilters {
  limit?: number;
  offset?: number;
  category?: string;
  severity?: string;
  entityType?: string;
  entityId?: string;
  start?: string;
  end?: string;
  search?: string;
}

export async function fetchAuditLog(filters: AuditLogFilters): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit ?? 100));
  params.set("offset", String(filters.offset ?? 0));
  if (filters.category) params.set("category", filters.category);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.entityType) params.set("entity_type", filters.entityType);
  if (filters.entityId) params.set("entity_id", filters.entityId);
  if (filters.start) params.set("start", filters.start);
  if (filters.end) params.set("end", filters.end);
  if (filters.search) params.set("search", filters.search);
  return apiGet(`/customer/audit-log?${params.toString()}`);
}

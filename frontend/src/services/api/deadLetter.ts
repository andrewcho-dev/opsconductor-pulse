import keycloak from "@/services/auth/keycloak";
import { ApiError } from "./client";

export interface DeadLetterMessage {
  id: number;
  tenant_id: string;
  route_id: number | null;
  route_name: string | null;
  original_topic: string;
  payload: Record<string, unknown>;
  destination_type: string;
  destination_config: Record<string, unknown>;
  error_message: string | null;
  attempts: number;
  status: "FAILED" | "REPLAYED" | "DISCARDED";
  created_at: string;
  replayed_at: string | null;
}

export interface DeadLetterListResponse {
  messages: DeadLetterMessage[];
  total: number;
  limit: number;
  offset: number;
}

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

async function getAuthHeaders(method?: string): Promise<Record<string, string>> {
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch (error) {
      console.error("Auth token refresh failed:", error);
      keycloak.login();
      throw new ApiError(401, "Token expired");
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (keycloak.token) {
    headers["Authorization"] = `Bearer ${keycloak.token}`;
  }

  const csrfToken = getCsrfToken();
  const upperMethod = method?.toUpperCase();
  if (csrfToken && upperMethod && ["POST", "PUT", "PATCH", "DELETE"].includes(upperMethod)) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  return headers;
}

async function apiGetJson<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders("GET");
  const res = await fetch(path, { headers });
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, `API error: ${res.status}`, body);
  }
  return res.json();
}

async function apiPostJson<T>(path: string, data: unknown): Promise<T> {
  const headers = await getAuthHeaders("POST");
  const res = await fetch(path, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, `API error: ${res.status}`, body);
  }
  return res.json();
}

async function apiDeleteJson<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders("DELETE");
  const res = await fetch(path, { method: "DELETE", headers });
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, `API error: ${res.status}`, body);
  }
  return res.json();
}

export async function fetchDeadLetterMessages(params: {
  status?: string;
  route_id?: number;
  limit?: number;
  offset?: number;
}): Promise<DeadLetterListResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.route_id) query.set("route_id", String(params.route_id));
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));
  return apiGetJson(`/api/v1/customer/dead-letter?${query.toString()}`);
}

export async function replayDeadLetter(id: number): Promise<{ id: number; status: string }> {
  return apiPostJson(`/api/v1/customer/dead-letter/${id}/replay`, {});
}

export async function replayDeadLetterBatch(ids: number[]): Promise<{
  results: Array<{ id: number; status: string; error?: string }>;
  total: number;
  replayed: number;
  failed: number;
}> {
  return apiPostJson("/api/v1/customer/dead-letter/replay-batch", { ids });
}

export async function discardDeadLetter(id: number): Promise<{ id: number; status: string }> {
  return apiDeleteJson(`/api/v1/customer/dead-letter/${id}`);
}

export async function purgeDeadLetter(olderThanDays: number): Promise<{
  purged: number;
  older_than_days: number;
}> {
  return apiDeleteJson(
    `/api/v1/customer/dead-letter/purge?older_than_days=${olderThanDays}`
  );
}


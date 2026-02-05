import keycloak from "@/services/auth/keycloak";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  // Ensure token is fresh (refresh if < 30s remaining)
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch {
      // Token refresh failed — Keycloak will redirect to login
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

  return headers;
}

export async function apiGet<T>(path: string): Promise<T> {
  const headers = await getAuthHeaders();
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

export async function apiPost<T>(path: string, data: unknown): Promise<T> {
  const headers = await getAuthHeaders();
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

export async function apiPatch<T>(path: string, data: unknown): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(path, {
    method: "PATCH",
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

export async function apiDelete(path: string): Promise<void> {
  const headers = await getAuthHeaders();
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
}

import keycloak from "@/services/auth/keycloak";
import { logger } from "@/lib/logger";

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

export function getCsrfToken(): string | null {
  if (_csrfToken) {
    return _csrfToken;
  }
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

let _csrfToken: string | null = null;

export function storeCsrfToken(token: string): void {
  _csrfToken = token;
}

export async function getAuthHeaders(method?: string): Promise<Record<string, string>> {
  // Ensure token is fresh (refresh if < 30s remaining)
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch (error) {
      logger.error("Auth token refresh failed:", error);
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

  const csrfToken = getCsrfToken();
  const upperMethod = method?.toUpperCase();
  if (csrfToken && upperMethod && ["POST", "PUT", "PATCH", "DELETE"].includes(upperMethod)) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  return headers;
}

export async function apiGet<T>(path: string): Promise<T> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(path, { headers });
    const csrfHeader = res.headers.get("X-CSRF-Token");
    if (csrfHeader) {
      storeCsrfToken(csrfHeader);
    }

    if (!res.ok) {
      let body: unknown;
      try {
        body = await res.json();
      } catch (error) {
        logger.error("API GET response parse failed:", error);
        body = await res.text();
      }
      throw new ApiError(res.status, `API error: ${res.status}`, body);
    }

    return res.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    logger.error(`API GET ${path} failed:`, error);
    throw new ApiError(0, "Network error");
  }
}

export async function apiPost<T>(path: string, data: unknown): Promise<T> {
  try {
    const headers = await getAuthHeaders("POST");
    const res = await fetch(path, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
    const csrfHeader = res.headers.get("X-CSRF-Token");
    if (csrfHeader) {
      storeCsrfToken(csrfHeader);
    }

    if (!res.ok) {
      let body: unknown;
      try {
        body = await res.json();
      } catch (error) {
        logger.error("API POST response parse failed:", error);
        body = await res.text();
      }
      throw new ApiError(res.status, `API error: ${res.status}`, body);
    }

    return res.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    logger.error(`API POST ${path} failed:`, error);
    throw new ApiError(0, "Network error");
  }
}

export async function apiPut<T>(path: string, data: unknown): Promise<T> {
  try {
    const headers = await getAuthHeaders("PUT");
    const res = await fetch(path, {
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });
    const csrfHeader = res.headers.get("X-CSRF-Token");
    if (csrfHeader) {
      storeCsrfToken(csrfHeader);
    }

    if (!res.ok) {
      let body: unknown;
      try {
        body = await res.json();
      } catch (error) {
        logger.error("API PUT response parse failed:", error);
        body = await res.text();
      }
      throw new ApiError(res.status, `API error: ${res.status}`, body);
    }

    return res.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    logger.error(`API PUT ${path} failed:`, error);
    throw new ApiError(0, "Network error");
  }
}

export async function apiPatch<T>(path: string, data: unknown): Promise<T> {
  try {
    const headers = await getAuthHeaders("PATCH");
    const res = await fetch(path, {
      method: "PATCH",
      headers,
      body: JSON.stringify(data),
    });
    const csrfHeader = res.headers.get("X-CSRF-Token");
    if (csrfHeader) {
      storeCsrfToken(csrfHeader);
    }

    if (!res.ok) {
      let body: unknown;
      try {
        body = await res.json();
      } catch (error) {
        logger.error("API PATCH response parse failed:", error);
        body = await res.text();
      }
      throw new ApiError(res.status, `API error: ${res.status}`, body);
    }

    return res.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    logger.error(`API PATCH ${path} failed:`, error);
    throw new ApiError(0, "Network error");
  }
}

export async function apiDelete(path: string): Promise<void> {
  try {
    const headers = await getAuthHeaders("DELETE");
    const res = await fetch(path, { method: "DELETE", headers });
    const csrfHeader = res.headers.get("X-CSRF-Token");
    if (csrfHeader) {
      storeCsrfToken(csrfHeader);
    }

    if (!res.ok) {
      let body: unknown;
      try {
        body = await res.json();
      } catch (error) {
        logger.error("API DELETE response parse failed:", error);
        body = await res.text();
      }
      throw new ApiError(res.status, `API error: ${res.status}`, body);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    logger.error(`API DELETE ${path} failed:`, error);
    throw new ApiError(0, "Network error");
  }
}

# Task 002: Keycloak Authentication Integration

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

The React SPA needs to authenticate with Keycloak using the PKCE authorization code flow. The existing Keycloak realm (`pulse`) has a public client `pulse-ui` with PKCE S256 enabled and wildcard redirect URIs.

**Key auth facts**:
- Client ID: `pulse-ui` (public client, no secret)
- Keycloak URL: `http://localhost:8180` (from env var `VITE_KEYCLOAK_URL`)
- Realm: `pulse`
- PKCE: Required (S256)
- JWT custom claims: `tenant_id`, `role` (in addition to standard `sub`, `email`, etc.)
- Token lifespan: 900s (15 min), auto-refresh via keycloak-js
- The existing Jinja2 UI uses httpOnly cookies — the React SPA does NOT. It uses in-memory tokens with `Authorization: Bearer` headers.

**Read first**:
- `frontend/src/App.tsx` — current minimal app from Task 1
- `frontend/.env` — Keycloak env vars

---

## Task

### 2.1 Install keycloak-js

```bash
cd /home/opsconductor/simcloud/frontend
npm install keycloak-js
```

### 2.2 Create Keycloak service

**File**: `frontend/src/services/auth/keycloak.ts` (NEW)

This file initializes the Keycloak instance. It does NOT import React — it's a plain TypeScript singleton.

```typescript
import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8180",
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "pulse",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "pulse-ui",
});

export default keycloak;
```

### 2.3 Create auth types

**File**: `frontend/src/services/auth/types.ts` (NEW)

```typescript
export interface PulseUser {
  sub: string;
  email: string;
  tenantId: string;
  role: string;
  name?: string;
}

export interface AuthContextValue {
  authenticated: boolean;
  user: PulseUser | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  isCustomer: boolean;
  isOperator: boolean;
}
```

### 2.4 Create AuthProvider

**File**: `frontend/src/services/auth/AuthProvider.tsx` (NEW)

This component wraps the entire app. It initializes Keycloak on mount, handles the OIDC flow, extracts user info from the JWT, and sets up automatic token refresh.

```tsx
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import keycloak from "./keycloak";
import type { AuthContextValue, PulseUser } from "./types";

const AuthContext = createContext<AuthContextValue>({
  authenticated: false,
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  isCustomer: false,
  isOperator: false,
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

function extractUser(): PulseUser | null {
  if (!keycloak.tokenParsed) return null;
  const tp = keycloak.tokenParsed as Record<string, unknown>;
  return {
    sub: (tp.sub as string) || "",
    email: (tp.email as string) || "",
    tenantId: (tp.tenant_id as string) || "",
    role: (tp.role as string) || "",
    name: (tp.preferred_username as string) || (tp.name as string) || "",
  };
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<PulseUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    keycloak
      .init({
        onLoad: "login-required",
        pkceMethod: "S256",
        checkLoginIframe: false,
      })
      .then((auth) => {
        if (auth) {
          setAuthenticated(true);
          setUser(extractUser());
          setToken(keycloak.token || null);
        }
        setInitialized(true);
      })
      .catch((err) => {
        console.error("Keycloak init failed:", err);
        setError("Authentication service unavailable");
        setInitialized(true);
      });

    // Token refresh: refresh when token has < 60 seconds remaining
    const refreshInterval = setInterval(() => {
      if (keycloak.authenticated) {
        keycloak
          .updateToken(60)
          .then((refreshed) => {
            if (refreshed) {
              setToken(keycloak.token || null);
              setUser(extractUser());
            }
          })
          .catch(() => {
            console.warn("Token refresh failed, redirecting to login");
            keycloak.login();
          });
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(refreshInterval);
  }, []);

  const login = useCallback(() => {
    keycloak.login();
  }, []);

  const logout = useCallback(() => {
    keycloak.logout({ redirectUri: window.location.origin + "/app/" });
  }, []);

  const role = user?.role || "";
  const isCustomer = role === "customer_admin" || role === "customer_viewer";
  const isOperator = role === "operator" || role === "operator_admin";

  if (!initialized) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-muted-foreground">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-destructive text-lg">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{ authenticated, user, token, login, logout, isCustomer, isOperator }}
    >
      {children}
    </AuthContext.Provider>
  );
}
```

### 2.5 Create API client with auth header injection

**File**: `frontend/src/services/api/client.ts` (NEW)

A thin fetch wrapper that automatically injects the Bearer token from Keycloak. All API calls go through this client.

```typescript
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
```

### 2.6 Update App.tsx to use AuthProvider

**File**: `frontend/src/App.tsx` (MODIFY)

```tsx
import { AuthProvider, useAuth } from "@/services/auth/AuthProvider";

function AppContent() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold text-primary">OpsConductor Pulse</h1>
        <p className="text-muted-foreground">Authenticated as: {user?.email}</p>
        <p className="text-sm text-muted-foreground">
          Tenant: {user?.tenantId} | Role: {user?.role}
        </p>
        <button
          onClick={logout}
          className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-accent"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
```

### 2.7 Export auth modules

**File**: `frontend/src/services/auth/index.ts` (NEW)

```typescript
export { AuthProvider, useAuth } from "./AuthProvider";
export { default as keycloak } from "./keycloak";
export type { PulseUser, AuthContextValue } from "./types";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/services/auth/keycloak.ts` | Keycloak instance singleton |
| CREATE | `frontend/src/services/auth/types.ts` | Auth type definitions |
| CREATE | `frontend/src/services/auth/AuthProvider.tsx` | React auth context provider |
| CREATE | `frontend/src/services/auth/index.ts` | Auth module exports |
| CREATE | `frontend/src/services/api/client.ts` | API client with Bearer auth |
| MODIFY | `frontend/src/App.tsx` | Wrap in AuthProvider, show user info |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript types

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Verify existing backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

### Step 4: Verify implementation

Read the files and confirm:
- [ ] `keycloak.ts` reads env vars for URL, realm, clientId
- [ ] `AuthProvider` calls `keycloak.init()` with `onLoad: "login-required"` and `pkceMethod: "S256"`
- [ ] `AuthProvider` extracts `tenant_id` and `role` from JWT claims
- [ ] Token refresh runs every 30 seconds via `keycloak.updateToken(60)`
- [ ] `AuthProvider` shows loading spinner during initialization
- [ ] `AuthProvider` shows error state with retry button if Keycloak unavailable
- [ ] `client.ts` injects `Authorization: Bearer` header on all requests
- [ ] `client.ts` refreshes token before requests if < 30s remaining
- [ ] `App.tsx` wraps content in `AuthProvider`
- [ ] `useAuth()` hook exported for child components

---

## Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] `keycloak-js` installed as dependency
- [ ] `AuthProvider` wraps entire app
- [ ] JWT `tenant_id` and `role` claims extracted into `PulseUser` type
- [ ] Loading state shown during Keycloak initialization
- [ ] Error state with retry shown if Keycloak unavailable
- [ ] API client injects Bearer token automatically
- [ ] Token auto-refresh every 30s
- [ ] `useAuth()` hook provides `user`, `token`, `login`, `logout`, `isCustomer`, `isOperator`
- [ ] All Python tests pass

---

## Commit

```
Add Keycloak authentication to React frontend

keycloak-js integration with PKCE S256. AuthProvider context
with auto token refresh. API client injects Bearer header.
Loading and error states for auth initialization.

Phase 18 Task 2: Auth Integration
```

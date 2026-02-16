# 005 — Frontend PermissionProvider + usePermissions Hook

## Task

Create a React context provider that fetches the current user's effective permissions from the backend and exposes them via a `usePermissions()` hook. Integrate it into the existing auth flow.

## Context

### Existing auth pattern

File: `frontend/src/services/auth/AuthProvider.tsx`
- Wraps app with Keycloak auth
- Provides `useAuth()` hook returning `{ authenticated, user, token, login, logout, isCustomer, isOperator }`
- `user` is a `PulseUser` with `sub`, `email`, `tenantId`, `role`, `realmAccess.roles`, etc.

File: `frontend/src/services/auth/types.ts`
```typescript
interface PulseUser {
  sub: string;
  email: string;
  tenantId: string;
  role: string;
  organization?: Record<string, object> | string[];
  realmAccess?: { roles: string[] };
  name?: string;
}

interface AuthContextValue {
  authenticated: boolean;
  user: PulseUser | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  isCustomer: boolean;
  isOperator: boolean;
}
```

File: `frontend/src/services/auth/index.ts`
```typescript
export { AuthProvider, useAuth } from "./AuthProvider";
export { default as keycloak } from "./keycloak";
export type { PulseUser, AuthContextValue } from "./types";
```

### API client pattern

File: `frontend/src/services/api/client.ts`
- `apiGet<T>(path: string): Promise<T>` — adds Bearer token and CSRF headers automatically

### React Query pattern

File: `frontend/src/hooks/use-alert-rules.ts` (representative):
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
export function useAlertRules(limit = 100) {
  return useQuery({
    queryKey: ["alert-rules", limit],
    queryFn: () => fetchAlertRules(limit),
  });
}
```

## Step 1: Create API functions

### Create File: `frontend/src/services/api/roles.ts`

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";

export interface Permission {
  id: number;
  action: string;
  category: string;
  description: string;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  permissions: Permission[];
  created_at: string;
  updated_at: string;
}

export interface RoleAssignment {
  id: string;
  role_id: string;
  role_name: string;
  is_system: boolean;
  assigned_at: string;
  assigned_by: string;
}

export interface MyPermissionsResponse {
  permissions: string[];
  roles: string[];
}

// Self-service
export async function fetchMyPermissions(): Promise<MyPermissionsResponse> {
  return apiGet("/customer/me/permissions");
}

// Admin endpoints
export async function fetchPermissions(): Promise<{ permissions: Permission[] }> {
  return apiGet("/customer/permissions");
}

export async function fetchRoles(): Promise<{ roles: Role[] }> {
  return apiGet("/customer/roles");
}

export async function createRole(data: {
  name: string;
  description: string;
  permission_ids: number[];
}): Promise<{ id: string; message: string }> {
  return apiPost("/customer/roles", data);
}

export async function updateRole(
  roleId: string,
  data: { name?: string; description?: string; permission_ids?: number[] }
): Promise<{ message: string }> {
  return apiPut(`/customer/roles/${roleId}`, data);
}

export async function deleteRole(roleId: string): Promise<void> {
  return apiDelete(`/customer/roles/${roleId}`);
}

export async function fetchUserAssignments(
  userId: string
): Promise<{ assignments: RoleAssignment[] }> {
  return apiGet(`/customer/users/${userId}/assignments`);
}

export async function updateUserAssignments(
  userId: string,
  roleIds: string[]
): Promise<{ message: string }> {
  return apiPut(`/customer/users/${userId}/assignments`, { role_ids: roleIds });
}
```

### Update `frontend/src/services/api/index.ts`

Add the export:
```typescript
export * from "./roles";
```

## Step 2: Create PermissionProvider

### Create File: `frontend/src/services/auth/PermissionProvider.tsx`

```typescript
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import { fetchMyPermissions } from "@/services/api/roles";

interface PermissionContextValue {
  permissions: Set<string>;
  hasPermission: (action: string) => boolean;
  loading: boolean;
  refetchPermissions: () => void;
}

const PermissionContext = createContext<PermissionContextValue>({
  permissions: new Set(),
  hasPermission: () => false,
  loading: true,
  refetchPermissions: () => {},
});

export function PermissionProvider({ children }: { children: ReactNode }) {
  const { authenticated, isOperator, isCustomer } = useAuth();
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const loadPermissions = useCallback(async () => {
    if (!authenticated) {
      setPermissions(new Set());
      setLoading(false);
      return;
    }

    // Operators have all permissions — no need to fetch
    if (isOperator) {
      setPermissions(new Set(["*"]));
      setLoading(false);
      return;
    }

    // Only fetch for customers
    if (!isCustomer) {
      setPermissions(new Set());
      setLoading(false);
      return;
    }

    try {
      const data = await fetchMyPermissions();
      setPermissions(new Set(data.permissions));
    } catch (error) {
      console.error("Failed to load permissions:", error);
      setPermissions(new Set());
    } finally {
      setLoading(false);
    }
  }, [authenticated, isOperator, isCustomer]);

  useEffect(() => {
    loadPermissions();
  }, [loadPermissions]);

  const hasPermission = useCallback(
    (action: string) => {
      if (isOperator) return true;
      return permissions.has("*") || permissions.has(action);
    },
    [permissions, isOperator]
  );

  return (
    <PermissionContext.Provider
      value={{ permissions, hasPermission, loading, refetchPermissions: loadPermissions }}
    >
      {children}
    </PermissionContext.Provider>
  );
}

export function usePermissions() {
  return useContext(PermissionContext);
}
```

## Step 3: Update types

### Modify `frontend/src/services/auth/types.ts`

Add the permission types (append, don't replace existing):

```typescript
export interface PermissionContextValue {
  permissions: Set<string>;
  hasPermission: (action: string) => boolean;
  loading: boolean;
  refetchPermissions: () => void;
}
```

## Step 4: Update auth barrel export

### Modify `frontend/src/services/auth/index.ts`

Add exports for the new provider:

```typescript
export { AuthProvider, useAuth } from "./AuthProvider";
export { PermissionProvider, usePermissions } from "./PermissionProvider";
export { default as keycloak } from "./keycloak";
export type { PulseUser, AuthContextValue, PermissionContextValue } from "./types";
```

## Step 5: Integrate PermissionProvider into app

### Modify `frontend/src/App.tsx` (or wherever AuthProvider wraps the app)

Find where `<AuthProvider>` wraps the app tree. Add `<PermissionProvider>` inside it:

```tsx
<AuthProvider>
  <PermissionProvider>
    {/* rest of app */}
  </PermissionProvider>
</AuthProvider>
```

Look for this in either:
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/app/providers.tsx`

The `PermissionProvider` must be INSIDE `AuthProvider` because it uses `useAuth()`.

## Step 6: Create React Query hooks

### Create File: `frontend/src/hooks/use-roles.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPermissions,
  fetchRoles,
  createRole,
  updateRole,
  deleteRole,
  fetchUserAssignments,
  updateUserAssignments,
} from "@/services/api/roles";

export function usePermissionsList() {
  return useQuery({
    queryKey: ["permissions-list"],
    queryFn: () => fetchPermissions(),
  });
}

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: () => fetchRoles(),
  });
}

export function useCreateRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createRole,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roles"] }),
  });
}

export function useUpdateRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ roleId, data }: { roleId: string; data: Parameters<typeof updateRole>[1] }) =>
      updateRole(roleId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roles"] }),
  });
}

export function useDeleteRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (roleId: string) => deleteRole(roleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roles"] }),
  });
}

export function useUserAssignments(userId: string) {
  return useQuery({
    queryKey: ["user-assignments", userId],
    queryFn: () => fetchUserAssignments(userId),
    enabled: !!userId,
  });
}

export function useUpdateUserAssignments() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, roleIds }: { userId: string; roleIds: string[] }) =>
      updateUserAssignments(userId, roleIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["user-assignments"] });
      qc.invalidateQueries({ queryKey: ["tenant-users"] });
    },
  });
}
```

## Verification

- `usePermissions()` returns `{ permissions, hasPermission, loading, refetchPermissions }`
- For an operator user, `hasPermission("anything")` returns `true`
- For a customer with Full Admin role, `hasPermission("devices.read")` returns `true`
- For a customer with Viewer role, `hasPermission("devices.write")` returns `false`
- Loading state is `true` initially, then `false` after fetch completes
- `refetchPermissions()` re-fetches when role assignments change

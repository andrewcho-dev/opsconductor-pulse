# Create Frontend API Client and Hooks for User Management

Create the API client functions and React Query hooks for user management.

## Files to Create

### 1. `frontend/src/services/api/users.ts`

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";

// Types
export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  enabled: boolean;
  email_verified: boolean;
  created_at: number | null;
  tenant_id: string | null;
  roles: string[];
  attributes: Record<string, string[]>;
}

export interface UsersResponse {
  users: User[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  temporary_password?: string;
  tenant_id?: string;
  role?: string;
}

export interface InviteUserRequest {
  email: string;
  first_name?: string;
  last_name?: string;
  role?: string;
}

export interface UpdateUserRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  enabled?: boolean;
}

export interface AssignRoleRequest {
  role: string;
}

export interface AssignTenantRequest {
  tenant_id: string;
}

export interface Organization {
  id: string;
  name: string;
  alias?: string;
  enabled: boolean;
}

// ============== OPERATOR API ==============

export async function fetchOperatorUsers(
  search?: string,
  tenantFilter?: string,
  limit = 100,
  offset = 0
): Promise<UsersResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (search) params.set("search", search);
  if (tenantFilter) params.set("tenant_filter", tenantFilter);
  return apiGet(`/operator/users?${params.toString()}`);
}

export async function fetchOperatorUser(userId: string): Promise<User> {
  return apiGet(`/operator/users/${userId}`);
}

export async function createOperatorUser(data: CreateUserRequest): Promise<{ id: string; username: string; message: string }> {
  return apiPost("/operator/users", data);
}

export async function updateOperatorUser(userId: string, data: UpdateUserRequest): Promise<{ message: string }> {
  return apiPut(`/operator/users/${userId}`, data);
}

export async function deleteOperatorUser(userId: string): Promise<{ message: string }> {
  return apiDelete(`/operator/users/${userId}`);
}

export async function enableOperatorUser(userId: string): Promise<{ message: string }> {
  return apiPost(`/operator/users/${userId}/enable`, {});
}

export async function disableOperatorUser(userId: string): Promise<{ message: string }> {
  return apiPost(`/operator/users/${userId}/disable`, {});
}

export async function assignOperatorUserRole(userId: string, role: string): Promise<{ message: string }> {
  return apiPost(`/operator/users/${userId}/roles`, { role });
}

export async function removeOperatorUserRole(userId: string, role: string): Promise<{ message: string }> {
  return apiDelete(`/operator/users/${userId}/roles/${role}`);
}

export async function assignOperatorUserTenant(userId: string, tenantId: string): Promise<{ message: string }> {
  return apiPost(`/operator/users/${userId}/tenant`, { tenant_id: tenantId });
}

export async function sendOperatorPasswordReset(userId: string): Promise<{ message: string }> {
  return apiPost(`/operator/users/${userId}/reset-password`, {});
}

export async function fetchOrganizations(): Promise<{ organizations: Organization[] }> {
  return apiGet("/operator/organizations");
}

// ============== CUSTOMER/TENANT API ==============

export async function fetchTenantUsers(
  search?: string,
  limit = 100,
  offset = 0
): Promise<UsersResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (search) params.set("search", search);
  return apiGet(`/customer/users?${params.toString()}`);
}

export async function fetchTenantUser(userId: string): Promise<User> {
  return apiGet(`/customer/users/${userId}`);
}

export async function inviteTenantUser(data: InviteUserRequest): Promise<{ id: string; username: string; email: string; message: string }> {
  return apiPost("/customer/users/invite", data);
}

export async function updateTenantUser(userId: string, data: UpdateUserRequest): Promise<{ message: string }> {
  return apiPut(`/customer/users/${userId}`, data);
}

export async function changeTenantUserRole(userId: string, role: string): Promise<{ message: string }> {
  return apiPost(`/customer/users/${userId}/role`, { role });
}

export async function removeTenantUser(userId: string): Promise<{ message: string }> {
  return apiDelete(`/customer/users/${userId}`);
}

export async function sendTenantPasswordReset(userId: string): Promise<{ message: string }> {
  return apiPost(`/customer/users/${userId}/reset-password`, {});
}
```

### 2. `frontend/src/hooks/use-users.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchOperatorUsers,
  fetchOperatorUser,
  createOperatorUser,
  updateOperatorUser,
  deleteOperatorUser,
  enableOperatorUser,
  disableOperatorUser,
  assignOperatorUserRole,
  removeOperatorUserRole,
  assignOperatorUserTenant,
  sendOperatorPasswordReset,
  fetchOrganizations,
  fetchTenantUsers,
  fetchTenantUser,
  inviteTenantUser,
  updateTenantUser,
  changeTenantUserRole,
  removeTenantUser,
  sendTenantPasswordReset,
  type CreateUserRequest,
  type UpdateUserRequest,
  type InviteUserRequest,
} from "@/services/api/users";

// ============== OPERATOR HOOKS ==============

export function useOperatorUsers(search?: string, tenantFilter?: string, limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["operator-users", search, tenantFilter, limit, offset],
    queryFn: () => fetchOperatorUsers(search, tenantFilter, limit, offset),
  });
}

export function useOperatorUser(userId: string) {
  return useQuery({
    queryKey: ["operator-user", userId],
    queryFn: () => fetchOperatorUser(userId),
    enabled: !!userId,
  });
}

export function useOrganizations() {
  return useQuery({
    queryKey: ["organizations"],
    queryFn: fetchOrganizations,
  });
}

export function useCreateOperatorUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUserRequest) => createOperatorUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
    },
  });
}

export function useUpdateOperatorUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UpdateUserRequest }) =>
      updateOperatorUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
      queryClient.invalidateQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useDeleteOperatorUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => deleteOperatorUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
    },
  });
}

export function useEnableOperatorUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => enableOperatorUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
      queryClient.invalidateQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useDisableOperatorUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => disableOperatorUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
      queryClient.invalidateQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useAssignOperatorUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      assignOperatorUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
      queryClient.invalidateQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useRemoveOperatorUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      removeOperatorUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
      queryClient.invalidateQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useAssignOperatorUserTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, tenantId }: { userId: string; tenantId: string }) =>
      assignOperatorUserTenant(userId, tenantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operator-users"] });
      queryClient.invalidateQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useSendOperatorPasswordReset() {
  return useMutation({
    mutationFn: (userId: string) => sendOperatorPasswordReset(userId),
  });
}

// ============== TENANT HOOKS ==============

export function useTenantUsers(search?: string, limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["tenant-users", search, limit, offset],
    queryFn: () => fetchTenantUsers(search, limit, offset),
  });
}

export function useTenantUser(userId: string) {
  return useQuery({
    queryKey: ["tenant-user", userId],
    queryFn: () => fetchTenantUser(userId),
    enabled: !!userId,
  });
}

export function useInviteTenantUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InviteUserRequest) => inviteTenantUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
    },
  });
}

export function useUpdateTenantUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UpdateUserRequest }) =>
      updateTenantUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      queryClient.invalidateQueries({ queryKey: ["tenant-user"] });
    },
  });
}

export function useChangeTenantUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      changeTenantUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      queryClient.invalidateQueries({ queryKey: ["tenant-user"] });
    },
  });
}

export function useRemoveTenantUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeTenantUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
    },
  });
}

export function useSendTenantPasswordReset() {
  return useMutation({
    mutationFn: (userId: string) => sendTenantPasswordReset(userId),
  });
}
```

### 3. Update `frontend/src/services/api/index.ts`

Add export:

```typescript
export * from "./users";
```

## Notes

- All hooks follow existing codebase patterns
- Mutations automatically invalidate related queries
- Separate hooks for operator and tenant contexts
- Types match backend response structure

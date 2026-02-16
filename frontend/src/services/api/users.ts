import { apiDelete, apiGet, apiPost, apiPut } from "./client";

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
  return apiGet(`/api/v1/operator/users?${params.toString()}`);
}

export async function fetchOperatorUser(userId: string): Promise<User> {
  return apiGet(`/api/v1/operator/users/${userId}`);
}

export async function createOperatorUser(
  data: CreateUserRequest
): Promise<{ id: string; username: string; message: string }> {
  return apiPost("/api/v1/operator/users", data);
}

export async function updateOperatorUser(
  userId: string,
  data: UpdateUserRequest
): Promise<{ message: string }> {
  return apiPut(`/api/v1/operator/users/${userId}`, data);
}

export async function deleteOperatorUser(userId: string): Promise<void> {
  return apiDelete(`/api/v1/operator/users/${userId}`);
}

export async function enableOperatorUser(userId: string): Promise<{ message: string }> {
  return apiPost(`/api/v1/operator/users/${userId}/enable`, {});
}

export async function disableOperatorUser(userId: string): Promise<{ message: string }> {
  return apiPost(`/api/v1/operator/users/${userId}/disable`, {});
}

export async function assignOperatorUserRole(
  userId: string,
  role: string
): Promise<{ message: string }> {
  return apiPost(`/api/v1/operator/users/${userId}/roles`, { role });
}

export async function removeOperatorUserRole(
  userId: string,
  role: string
): Promise<void> {
  return apiDelete(`/api/v1/operator/users/${userId}/roles/${role}`);
}

export async function assignOperatorUserTenant(
  userId: string,
  tenantId: string
): Promise<{ message: string }> {
  return apiPost(`/api/v1/operator/users/${userId}/tenant`, { tenant_id: tenantId });
}

export async function sendOperatorPasswordReset(userId: string): Promise<{ message: string }> {
  return apiPost(`/api/v1/operator/users/${userId}/reset-password`, {});
}

export async function fetchOrganizations(): Promise<{ organizations: Organization[] }> {
  return apiGet("/api/v1/operator/organizations");
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
  return apiGet(`/api/v1/customer/users?${params.toString()}`);
}

export async function fetchTenantUser(userId: string): Promise<User> {
  return apiGet(`/api/v1/customer/users/${userId}`);
}

export async function inviteTenantUser(
  data: InviteUserRequest
): Promise<{ id: string; username: string; email: string; message: string }> {
  return apiPost("/api/v1/customer/users/invite", data);
}

export async function updateTenantUser(
  userId: string,
  data: UpdateUserRequest
): Promise<{ message: string }> {
  return apiPut(`/api/v1/customer/users/${userId}`, data);
}

export async function changeTenantUserRole(
  userId: string,
  role: string
): Promise<{ message: string }> {
  return apiPost(`/api/v1/customer/users/${userId}/role`, { role });
}

export async function removeTenantUser(userId: string): Promise<void> {
  return apiDelete(`/api/v1/customer/users/${userId}`);
}

export async function sendTenantPasswordReset(userId: string): Promise<{ message: string }> {
  return apiPost(`/api/v1/customer/users/${userId}/reset-password`, {});
}

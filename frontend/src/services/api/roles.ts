import { apiDelete, apiGet, apiPost, apiPut } from "./client";

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
  data: { name?: string; description?: string; permission_ids?: number[] },
): Promise<{ message: string }> {
  return apiPut(`/customer/roles/${roleId}`, data);
}

export async function deleteRole(roleId: string): Promise<void> {
  return apiDelete(`/customer/roles/${roleId}`);
}

export async function fetchUserAssignments(
  userId: string,
): Promise<{ assignments: RoleAssignment[] }> {
  return apiGet(`/customer/users/${userId}/assignments`);
}

export async function updateUserAssignments(
  userId: string,
  roleIds: string[],
): Promise<{ message: string }> {
  return apiPut(`/customer/users/${userId}/assignments`, { role_ids: roleIds });
}


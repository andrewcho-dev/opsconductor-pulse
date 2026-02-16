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


import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["operator-users"] });
      await queryClient.refetchQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useRemoveOperatorUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      removeOperatorUserRole(userId, role),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["operator-users"] });
      await queryClient.refetchQueries({ queryKey: ["operator-user"] });
    },
  });
}

export function useAssignOperatorUserTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, tenantId }: { userId: string; tenantId: string }) =>
      assignOperatorUserTenant(userId, tenantId),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["operator-users"] });
      await queryClient.refetchQueries({ queryKey: ["operator-user"] });
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
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["tenant-users"] });
      await queryClient.refetchQueries({ queryKey: ["tenant-user"] });
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

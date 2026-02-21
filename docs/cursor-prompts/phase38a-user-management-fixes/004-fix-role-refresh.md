# Fix Role Badge Refresh After Change

## Problem

After changing a user's role (especially promoting User → Admin), the role badge in the table doesn't reliably update. The data appears stale even after `invalidateQueries()` fires.

## Root Cause

React Query's `invalidateQueries()` marks queries as stale but doesn't guarantee immediate refetch before component re-renders. The mutation's `onSuccess` callback fires, the dialog closes, but the list may still show cached data.

## Fix

### 1. Update `frontend/src/hooks/use-users.ts`

Use `refetchQueries` instead of just `invalidateQueries` for immediate refresh:

```typescript
export function useChangeTenantUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      changeTenantUserRole(userId, role),
    onSuccess: async () => {
      // Force immediate refetch instead of just invalidating
      await queryClient.refetchQueries({ queryKey: ["tenant-users"] });
      await queryClient.refetchQueries({ queryKey: ["tenant-user"] });
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
```

### 2. Update dialog close to wait for refetch

In `frontend/src/features/users/ChangeRoleDialog.tsx`:

```tsx
export function ChangeRoleDialog({
  userId,
  open,
  onOpenChange,
  onChanged,
}: ChangeRoleDialogProps) {
  // ... existing code ...

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (role === currentRole) {
      onChanged();
      return;
    }

    try {
      await changeMutation.mutateAsync({ userId, role });
      // The mutation's onSuccess will refetch queries
      // Wait a tick to ensure refetch completes before closing
      setTimeout(() => {
        onChanged();
      }, 100);
    } catch (error) {
      // Error shown via mutation state
    }
  };

  // ... rest of component
}
```

### 3. Alternative: Use optimistic updates

For instant feedback, add optimistic update to the mutation:

```typescript
export function useChangeTenantUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      changeTenantUserRole(userId, role),
    onMutate: async ({ userId, role }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["tenant-users"] });

      // Snapshot previous value
      const previousUsers = queryClient.getQueryData(["tenant-users"]);

      // Optimistically update the cache
      queryClient.setQueryData(["tenant-users"], (old: any) => {
        if (!old?.users) return old;
        return {
          ...old,
          users: old.users.map((user: any) => {
            if (user.id === userId) {
              // Update roles array
              const newRoles = user.roles.filter(
                (r: string) => r !== "customer" && r !== "tenant-admin"
              );
              newRoles.push(role);
              return { ...user, roles: newRoles };
            }
            return user;
          }),
        };
      });

      return { previousUsers };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousUsers) {
        queryClient.setQueryData(["tenant-users"], context.previousUsers);
      }
    },
    onSettled: () => {
      // Always refetch to ensure server state
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
    },
  });
}
```

### 4. Apply same pattern to tenant assignment

Update `useAssignOperatorUserTenant` hook similarly:

```typescript
export function useAssignOperatorUserTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, tenantId }: { userId: string; tenantId: string }) =>
      assignOperatorUserTenant(userId, tenantId),
    onSuccess: async () => {
      // Force immediate refetch
      await queryClient.refetchQueries({ queryKey: ["operator-users"] });
      await queryClient.refetchQueries({ queryKey: ["operator-user"] });
    },
  });
}
```

## Verification

1. Open tenant `/users` page
2. Change a user's role from User to Admin
3. Dialog closes - badge should immediately show "Admin"
4. Refresh page - badge should still show "Admin"
5. Repeat for operator UI role assignment

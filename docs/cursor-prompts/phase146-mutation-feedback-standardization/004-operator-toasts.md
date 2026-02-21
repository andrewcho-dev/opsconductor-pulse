# Task 4: Add Toast Feedback to Operator/Admin Mutations

## Context

8 operator files contain 19 mutations. Some have `console.error()` in `onError` which must be replaced with `toast.error()`. Others have no error handling at all.

## Pattern

Same as previous tasks. Add `import { toast } from "sonner"` and `import { getErrorMessage } from "@/lib/errors"`. Add toast in `onSuccess`, add/replace `onError`.

**Important:** Where `onError` currently does `console.error(...)`, REPLACE it with `toast.error(...)` — do not keep both.

## File 1: `frontend/src/features/operator/CreateTenantDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

Current `onError` (line ~100):
```typescript
onError: (error: Error) => {
  console.error("Create tenant error:", getErrorMessage(error));
},
```

Replace with:
```typescript
onError: (err: Error) => {
  toast.error(getErrorMessage(err) || "Failed to create tenant");
},
```

Add to `onSuccess`:
```typescript
toast.success("Tenant created");
```

## File 2: `frontend/src/features/operator/EditTenantDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `mutation` (updateTenant) | `"Tenant updated"` | `"Failed to update tenant"` |

## File 3: `frontend/src/features/operator/CreateSubscriptionDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `mutation` (apiPost) | `"Subscription created"` | `"Failed to create subscription"` |

## File 4: `frontend/src/features/operator/EditSubscriptionDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `mutation` (apiPost) | `"Subscription updated"` | `"Failed to update subscription"` |

## File 5: `frontend/src/features/operator/StatusChangeDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `mutation` (apiPatch) | `"Status updated"` | `"Failed to update status"` |

## File 6: `frontend/src/features/operator/BulkAssignDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `mutation` (bulk apiPost loop) | `"Devices assigned"` | `"Failed to assign devices"` |

## File 7: `frontend/src/features/operator/OperatorTenantsPage.tsx`

This file already imports `toast` if added in Phase 145. Check — if not, add it.

Add import: `getErrorMessage` from `"@/lib/errors"` (if not present)

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `deleteMutation` (deleteTenant) | `"Tenant deleted"` | `"Failed to delete tenant"` |

## File 8: `frontend/src/features/operator/UserListPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMut` (createOperatorUser) | `"User created"` | `"Failed to create user"` |
| `deleteMut` (deleteOperatorUser) | `"User deleted"` | `"Failed to delete user"` |
| `resetMut` (sendOperatorPasswordReset) | `"Password reset email sent"` | `"Failed to send password reset"` |
| `roleMut` (assignOperatorUserRole) | `"Role assigned"` | `"Failed to assign role"` |
| `tenantMut` (assignOperatorUserTenant) | `"Tenant assigned"` | `"Failed to assign tenant"` |
| `enableMut` (enableOperatorUser) | `"User enabled"` | `"Failed to enable user"` |
| `disableMut` (disableOperatorUser) | `"User disabled"` | `"Failed to disable user"` |

Note: `resetMut` currently has NO `onSuccess` or `onError` at all. Add both.

## File 9: `frontend/src/features/operator/UserDetailPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `patchMut` (updateUser) | `"User updated"` | `"Failed to update user"` |
| `addRoleMut` (assignRole) | `"Role assigned"` | `"Failed to assign role"` |
| `removeRoleMut` (removeRole) | `"Role removed"` | `"Failed to remove role"` |
| `setPasswordMut` (resetUserPassword) | `"Password updated"` | `"Failed to update password"` |
| `sendResetMut` (sendPasswordReset) | `"Password reset email sent"` | `"Failed to send password reset"` |

Note: `setPasswordMut` and `sendResetMut` currently have NO callbacks at all. Add `onSuccess` with toast + query invalidation, and `onError` with toast.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

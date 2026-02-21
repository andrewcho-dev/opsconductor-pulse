# Hide Self-Targeting Actions in User Tables

## Problem

Users can see dangerous actions (disable, delete, remove) for their own account in the dropdown menus. While the backend blocks these operations, the UI should not present them.

## Fix

### 1. Update `frontend/src/features/operator/OperatorUsersPage.tsx`

Get current user ID from auth context and hide self-targeting actions:

```tsx
import { useAuth } from "@/services/auth/AuthProvider";

export default function OperatorUsersPage() {
  const { user: currentUser } = useAuth();
  const currentUserId = currentUser?.sub;

  // ... existing code ...

  return (
    // ... existing JSX ...
    {users.map((user) => {
      const isSelf = user.id === currentUserId;

      return (
        <TableRow key={user.id}>
          {/* ... other cells ... */}
          <TableCell>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setEditUserId(user.id)}>
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </DropdownMenuItem>

                {/* Only show role/tenant assignment for non-self */}
                {!isSelf && (
                  <>
                    <DropdownMenuItem onClick={() => setAssignRoleUserId(user.id)}>
                      <Shield className="h-4 w-4 mr-2" />
                      Assign Role
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setAssignTenantUserId(user.id)}>
                      <Building2 className="h-4 w-4 mr-2" />
                      Assign Tenant
                    </DropdownMenuItem>
                  </>
                )}

                <DropdownMenuSeparator />

                <DropdownMenuItem onClick={() => handleResetPassword(user.id)}>
                  <Key className="h-4 w-4 mr-2" />
                  Reset Password
                </DropdownMenuItem>

                {/* Only show enable/disable for non-self */}
                {!isSelf && (
                  <>
                    {user.enabled ? (
                      <DropdownMenuItem onClick={() => handleDisable(user.id)}>
                        <UserX className="h-4 w-4 mr-2" />
                        Disable
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem onClick={() => handleEnable(user.id)}>
                        <UserCheck className="h-4 w-4 mr-2" />
                        Enable
                      </DropdownMenuItem>
                    )}
                  </>
                )}

                {/* Only show delete for non-self */}
                {!isSelf && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleDelete(user.id)}
                      className="text-destructive"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </>
                )}

                {/* Show indicator for own account */}
                {isSelf && (
                  <>
                    <DropdownMenuSeparator />
                    <div className="px-2 py-1.5 text-xs text-muted-foreground">
                      This is your account
                    </div>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
      );
    })}
  );
}
```

### 2. Update `frontend/src/features/users/UsersPage.tsx`

Same pattern for tenant user list:

```tsx
import { useAuth } from "@/services/auth/AuthProvider";

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const currentUserId = currentUser?.sub;

  // ... existing code ...

  return (
    // ... in the table body ...
    {users.map((user) => {
      const isSelf = user.id === currentUserId;

      return (
        <TableRow key={user.id}>
          {/* ... other cells ... */}
          <TableCell>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setEditUserId(user.id)}>
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </DropdownMenuItem>

                {/* Only show role change for non-self */}
                {!isSelf && (
                  <DropdownMenuItem onClick={() => setChangeRoleUserId(user.id)}>
                    <Shield className="h-4 w-4 mr-2" />
                    Change Role
                  </DropdownMenuItem>
                )}

                <DropdownMenuSeparator />

                <DropdownMenuItem onClick={() => handleResetPassword(user.id)}>
                  <Key className="h-4 w-4 mr-2" />
                  Reset Password
                </DropdownMenuItem>

                {/* Only show remove for non-self */}
                {!isSelf && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleRemove(user.id, user.username)}
                      className="text-destructive"
                    >
                      <UserMinus className="h-4 w-4 mr-2" />
                      Remove from Team
                    </DropdownMenuItem>
                  </>
                )}

                {isSelf && (
                  <>
                    <DropdownMenuSeparator />
                    <div className="px-2 py-1.5 text-xs text-muted-foreground">
                      This is your account
                    </div>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
      );
    })}
  );
}
```

### 3. Verify `useAuth` exposes user sub

Check `frontend/src/services/auth/AuthProvider.tsx` exports user with `sub` field:

```tsx
// In the PulseUser type or interface, ensure sub is included:
interface PulseUser {
  sub: string;
  email: string;
  // ... other fields
}
```

## Verification

1. Login as operator_admin
2. Go to `/operator/users`
3. Find your own row - dropdown should NOT show Disable/Delete
4. Find another user's row - dropdown SHOULD show all actions
5. Repeat for tenant `/users` page

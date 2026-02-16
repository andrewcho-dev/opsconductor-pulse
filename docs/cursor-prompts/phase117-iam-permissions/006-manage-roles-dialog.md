# 006 — Replace ChangeRoleDialog with ManageUserRolesDialog

## Task

Create `ManageUserRolesDialog.tsx` that replaces the binary User/Admin radio group with a multi-select checkbox list of roles (system + custom) with a permission preview panel. Update `UsersPage.tsx` to use it.

## Context

### Current ChangeRoleDialog

File: `frontend/src/features/users/ChangeRoleDialog.tsx`
- Binary radio group: "User" (`customer`) or "Admin" (`tenant-admin`)
- Calls `POST /customer/users/{user_id}/role` with `{ role: "customer" | "tenant-admin" }`
- Uses `useChangeTenantUserRole()` hook from `use-users.ts`

### New approach

- Multi-select checkboxes for role bundles (system + custom)
- Shows effective permissions for selected roles
- Calls `PUT /customer/users/{user_id}/assignments` with `{ role_ids: [...] }`
- Uses `useUserAssignments()` and `useUpdateUserAssignments()` from `use-roles.ts`
- Uses `useRoles()` to list available roles

### UI component inventory (shadcn/ui available)

From `frontend/src/components/ui/`:
- `dialog.tsx` — Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
- `button.tsx` — Button
- `checkbox.tsx` — Checkbox (if exists, otherwise use radix Checkbox)
- `badge.tsx` — Badge
- `skeleton.tsx` — Skeleton
- `label.tsx` — Label

Check if `checkbox.tsx` exists in `frontend/src/components/ui/`. If not, create it using shadcn pattern, or use a simple `<input type="checkbox">` styled with Tailwind.

### UsersPage integration

File: `frontend/src/features/users/UsersPage.tsx`
- Line 26: `import { ChangeRoleDialog } from "./ChangeRoleDialog";`
- Line 45: `const [changeRoleUserId, setChangeRoleUserId] = useState<string | null>(null);`
- Lines 175-179: `<DropdownMenuItem onClick={() => setChangeRoleUserId(user.id)}>` Change Role
- Lines 264-274: `<ChangeRoleDialog>` rendered

## Create File: `frontend/src/features/users/ManageUserRolesDialog.tsx`

### Component Structure

```tsx
interface ManageUserRolesDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}
```

### Implementation

1. **Fetch current assignments:** `useUserAssignments(userId)` — gets current role_ids
2. **Fetch available roles:** `useRoles()` — gets all roles with their permissions
3. **Local state:** `selectedRoleIds: Set<string>` — initialized from current assignments
4. **On open:** Sync `selectedRoleIds` with current assignments via `useEffect`
5. **Save:** Call `useUpdateUserAssignments()` with the selected role IDs, then call `onSaved()` and `refetchPermissions()` from `usePermissions()`

### UI Layout

```
┌─────────────────────────────────────────────┐
│ Manage Roles                                │
├─────────────────────────────────────────────┤
│ Assigning roles for: **John Smith**         │
│                                             │
│ ┌─ System Roles ─────────────────────────┐  │
│ │ ☑ Viewer                               │  │
│ │   Read-only access to all areas        │  │
│ │ ☐ Device Manager                       │  │
│ │   Viewer + device management           │  │
│ │ ☐ Alert Manager                        │  │
│ │   Viewer + alert management            │  │
│ │ ☑ Team Admin                           │  │
│ │   Viewer + user management             │  │
│ │ ... etc                                │  │
│ └────────────────────────────────────────┘  │
│                                             │
│ ┌─ Custom Roles ─────────────────────────┐  │
│ │ ☐ Device Operator (if any exist)       │  │
│ └────────────────────────────────────────┘  │
│                                             │
│ ┌─ Effective Permissions ────────────────┐  │
│ │ dashboard.read, devices.read, ...      │  │
│ │ users.read, users.invite, ...          │  │
│ │ (grouped by category, shown as badges) │  │
│ └────────────────────────────────────────┘  │
│                                             │
│                      [Cancel] [Save Roles]  │
└─────────────────────────────────────────────┘
```

### Effective permissions preview

Compute the union of all permissions from selected roles (from the `roles` data which includes each role's permissions array). Display as badges grouped by category.

```tsx
const effectivePermissions = useMemo(() => {
  if (!rolesData?.roles) return [];
  const perms = new Map<string, { action: string; category: string }>();
  for (const role of rolesData.roles) {
    if (selectedRoleIds.has(role.id)) {
      for (const perm of role.permissions) {
        perms.set(perm.action, { action: perm.action, category: perm.category });
      }
    }
  }
  return Array.from(perms.values()).sort((a, b) => a.category.localeCompare(b.category) || a.action.localeCompare(b.action));
}, [rolesData, selectedRoleIds]);
```

### Key behaviors

- At least one role must be selected — disable Save if none selected
- Show loading skeleton while fetching roles/assignments
- Show error state from mutation
- After save, call `refetchPermissions()` from the `usePermissions()` hook to refresh the global permission state (in case the admin is editing their own team member's roles and the sidebar needs to update)

## Modify `frontend/src/features/users/UsersPage.tsx`

### Change import (line 26)

```typescript
// FROM:
import { ChangeRoleDialog } from "./ChangeRoleDialog";
// TO:
import { ManageUserRolesDialog } from "./ManageUserRolesDialog";
```

### Change label in dropdown (line 178)

```tsx
// FROM:
Change Role
// TO:
Manage Roles
```

### Change rendered dialog (lines 264-274)

```tsx
// FROM:
{changeRoleUserId && (
  <ChangeRoleDialog
    userId={changeRoleUserId}
    open={!!changeRoleUserId}
    onOpenChange={(open) => !open && setChangeRoleUserId(null)}
    onChanged={() => {
      setChangeRoleUserId(null);
      refetch();
    }}
  />
)}

// TO:
{changeRoleUserId && (
  <ManageUserRolesDialog
    userId={changeRoleUserId}
    open={!!changeRoleUserId}
    onOpenChange={(open) => !open && setChangeRoleUserId(null)}
    onSaved={() => {
      setChangeRoleUserId(null);
      refetch();
    }}
  />
)}
```

### Update role display in table

Currently line 66-70:
```tsx
const getRoleLabel = (roles: string[]) => {
  if (roles.includes("tenant-admin")) return "Admin";
  if (roles.includes("customer")) return "User";
  return roles[0] || "User";
};
```

This still works for backward compat (Keycloak roles). But consider also showing Pulse roles if available. For now, keep this as-is — the Keycloak roles display is acceptable until a future iteration shows DB role names.

## Do NOT delete ChangeRoleDialog.tsx

Leave the file in place for now — it can be removed in a cleanup pass later. Just stop importing/using it.

## Verification

- Opening "Manage Roles" for a user shows their current role assignments as checked
- Checking/unchecking roles updates the effective permissions preview in real-time
- Saving with selected roles calls PUT /customer/users/{id}/assignments
- After save, the user's permissions are updated
- Empty selection is prevented (Save button disabled)
- System roles and custom roles are shown in separate sections

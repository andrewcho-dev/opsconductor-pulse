# 008 — Update Sidebar + Route Guards to Use Permissions

## Task

Replace the hardcoded `canManageUsers` role check in `AppSidebar.tsx` with permission-based visibility, and replace `RequireTenantAdminOrOperator` in the router with a permission-aware guard.

## Context

### Current sidebar logic

File: `frontend/src/components/layout/AppSidebar.tsx`, lines 110-114:

```typescript
const roles = user?.realmAccess?.roles ?? [];
const canManageUsers =
  roles.includes("tenant-admin") ||
  roles.includes("operator") ||
  roles.includes("operator-admin");
```

This controls visibility of the "Team" nav item in Settings (line 148):
```typescript
const settingsNav: NavItem[] = [
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
  { label: "Notification Prefs", href: "/alerts", icon: Bell },
];
```

### Current route guard

File: `frontend/src/app/router.tsx`, lines 59-68:

```typescript
function RequireTenantAdminOrOperator() {
  const { user } = useAuth();
  const roles = user?.realmAccess?.roles ?? [];
  const allowed =
    roles.includes("tenant-admin") ||
    roles.includes("operator") ||
    roles.includes("operator-admin");
  if (!allowed) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
```

Used at lines 109-112:
```typescript
{
  element: <RequireTenantAdminOrOperator />,
  children: [{ path: "users", element: <UsersPage /> }],
},
```

## Changes to `frontend/src/components/layout/AppSidebar.tsx`

### 1. Add import

```typescript
import { usePermissions } from "@/services/auth";
```

### 2. Replace `canManageUsers` logic

Replace lines 110-114:

```typescript
// FROM:
const roles = user?.realmAccess?.roles ?? [];
const canManageUsers =
  roles.includes("tenant-admin") ||
  roles.includes("operator") ||
  roles.includes("operator-admin");

// TO:
const { hasPermission } = usePermissions();
const canManageUsers = hasPermission("users.read");
const canManageRoles = hasPermission("users.roles");
```

### 3. Add "Roles" nav item to settings

Replace lines 146-150:

```typescript
// FROM:
const settingsNav: NavItem[] = [
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
  { label: "Notification Prefs", href: "/alerts", icon: Bell },
];

// TO:
const settingsNav: NavItem[] = [
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
  ...(canManageRoles ? [{ label: "Roles", href: "/roles", icon: Shield }] : []),
  { label: "Notification Prefs", href: "/alerts", icon: Bell },
];
```

### 4. Add `Shield` to the lucide-react import

Add `Shield` to the destructured import from `lucide-react` at the top of the file (line ~2-26). Check if it's already imported — it's used elsewhere in the app. If already present, no change needed.

## Changes to `frontend/src/app/router.tsx`

### 1. Add import

```typescript
import { usePermissions } from "@/services/auth";
```

### 2. Replace `RequireTenantAdminOrOperator`

Replace lines 59-68 with a permission-aware guard:

```typescript
function RequirePermission({ permission, children }: { permission: string; children?: React.ReactNode }) {
  const { hasPermission, loading } = usePermissions();
  const { isOperator } = useAuth();

  // While permissions are loading, show nothing (prevents flash of redirect)
  if (loading && !isOperator) return null;

  if (!hasPermission(permission)) return <Navigate to="/dashboard" replace />;
  return children ? <>{children}</> : <Outlet />;
}
```

### 3. Update route usage

Replace lines 109-112:

```typescript
// FROM:
{
  element: <RequireTenantAdminOrOperator />,
  children: [{ path: "users", element: <UsersPage /> }],
},

// TO:
{
  element: <RequirePermission permission="users.read" />,
  children: [
    { path: "users", element: <UsersPage /> },
    { path: "roles", element: <RolesPage /> },
  ],
},
```

Wait — `RolesPage` needs `users.roles` permission, not `users.read`. Two options:

**Option A:** Use `users.read` as the parent guard (lighter), and let RolesPage do its own internal permission check (it already does from prompt 007).

**Option B:** Create separate route groups:

```typescript
{
  element: <RequirePermission permission="users.read" />,
  children: [{ path: "users", element: <UsersPage /> }],
},
{
  element: <RequirePermission permission="users.roles" />,
  children: [{ path: "roles", element: <RolesPage /> }],
},
```

**Use Option B** — it's cleaner and prevents even loading the RolesPage component if the user lacks permission.

### 4. Add RolesPage import

```typescript
import RolesPage from "@/features/roles/RolesPage";
```

If this import was already added in prompt 007 inside the `RequireCustomer` block, move it out of there and into the `RequirePermission` block instead. Remove the duplicate route entry.

### 5. Keep `RequireTenantAdminOrOperator` function

Don't delete it yet — it may be referenced elsewhere. Just stop using it for the `/users` route. If there are no other references, it's safe to remove.

## Optional: Additional sidebar gating

For a fuller implementation, you could also gate other sidebar sections by permission. This is optional for Phase 117 but listed here for reference:

```typescript
// In customerMonitoringNav or settingsNav:
// "Alert Rules" → hasPermission("alerts.rules.read")
// "Maintenance" → hasPermission("maintenance.read")
// "Notifications" → hasPermission("integrations.read")
```

**Don't implement these now** — they'd require additional route guards for each page and could break things. The current scope is just the Team/Roles nav items and their route guards.

## Verification

- User with `users.read` permission sees "Team" in sidebar
- User without `users.read` permission does NOT see "Team"
- User with `users.roles` permission sees "Roles" in sidebar
- Navigating directly to `/users` without `users.read` redirects to `/dashboard`
- Navigating directly to `/roles` without `users.roles` redirects to `/dashboard`
- Operator sees both "Team" and "Roles" (operator bypass)
- No flash of redirect while permissions are loading

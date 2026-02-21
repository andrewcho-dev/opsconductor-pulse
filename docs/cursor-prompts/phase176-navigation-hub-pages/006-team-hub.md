# Task 6: Team Hub Page

## Objective

Create a Team hub page that consolidates Users (Members) and Roles into a single page with 2 tabs. The Roles tab is conditionally rendered based on the `users.roles` permission.

## Files to Modify

1. `frontend/src/features/users/UsersPage.tsx` — add `embedded` prop
2. `frontend/src/features/roles/RolesPage.tsx` — add `embedded` prop

## File to Create

`frontend/src/features/users/TeamHubPage.tsx`

---

## Step 1: Modify UsersPage.tsx

Add `embedded` prop:

```tsx
export default function UsersPage({ embedded }: { embedded?: boolean }) {
```

Extract the PageHeader action ("Add User" / "Invite User" button) and conditionally render:

```tsx
const actions = (
  // ... existing action button JSX ...
);

{!embedded ? (
  <PageHeader
    title="Team Members"
    description="Manage users in your organization"
    action={actions}
  />
) : (
  <div className="flex justify-end gap-2 mb-4">{actions}</div>
)}
```

## Step 2: Modify RolesPage.tsx

Add `embedded` prop:

```tsx
export default function RolesPage({ embedded }: { embedded?: boolean }) {
```

Extract the PageHeader action ("Add Role" button) and conditionally render:

```tsx
const actions = (
  // ... existing action button JSX ...
);

{!embedded ? (
  <PageHeader
    title="Roles & Permissions"
    description="Manage role bundles for your organization"
    action={actions}
  />
) : (
  <div className="flex justify-end gap-2 mb-4">{actions}</div>
)}
```

## Step 3: Create TeamHubPage

**Create** `frontend/src/features/users/TeamHubPage.tsx`:

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { usePermissions } from "@/services/auth";
import UsersPage from "./UsersPage";
import RolesPage from "@/features/roles/RolesPage";

export default function TeamHubPage() {
  const [params, setParams] = useSearchParams();
  const { hasPermission } = usePermissions();
  const canManageRoles = hasPermission("users.roles");

  const tab = params.get("tab") ?? "members";
  // If user navigates to ?tab=roles but doesn't have permission, fall back to members
  const activeTab = tab === "roles" && !canManageRoles ? "members" : tab;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Team"
        description="Manage users and roles in your organization"
      />
      <Tabs
        value={activeTab}
        onValueChange={(v) => setParams({ tab: v }, { replace: true })}
      >
        <TabsList variant="line">
          <TabsTrigger value="members">Members</TabsTrigger>
          {canManageRoles && (
            <TabsTrigger value="roles">Roles</TabsTrigger>
          )}
        </TabsList>
        <TabsContent value="members" className="mt-4">
          <UsersPage embedded />
        </TabsContent>
        {canManageRoles && (
          <TabsContent value="roles" className="mt-4">
            <RolesPage embedded />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

export const Component = TeamHubPage;
```

**Key design decisions:**
- The Roles tab only renders if the user has `users.roles` permission
- If someone navigates to `/team?tab=roles` without the permission, they see the Members tab instead
- The hub page itself will be behind `RequirePermission("users.read")` in the router (Task 8)

## Verification

- `npx tsc --noEmit` passes
- TeamHubPage renders with Members tab (always visible)
- Roles tab appears only for users with `users.roles` permission
- Members tab shows user list with invite/edit/remove actions
- Roles tab shows system and custom roles with permission details
- Tab state in URL: `/team?tab=roles`

# Task 2: Flatten SettingsHubPage to 9 Flat Tabs

## Objective

Replace the 6-tab SettingsHubPage (which nests NotificationsHubPage and TeamHubPage) with a 9-tab flat layout that imports child components directly.

## File to Modify

`frontend/src/features/settings/SettingsHubPage.tsx`

## Current State (6 tabs, 2 nested)

```
General | Billing | Notifications(→3 sub-tabs) | Integrations | Team(→2 sub-tabs) | Profile
```

## Target State (9 flat tabs)

```
General | Billing | Channels | Delivery Log | Dead Letter | Integrations | Members | Roles | Profile
```

## Implementation

Replace the entire file contents:

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePermissions } from "@/services/auth";
import OrganizationPage from "./OrganizationPage";
import BillingPage from "./BillingPage";
import NotificationChannelsPage from "@/features/notifications/NotificationChannelsPage";
import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
import DeadLetterPage from "@/features/messaging/DeadLetterPage";
import CarrierIntegrationsPage from "./CarrierIntegrationsPage";
import UsersPage from "@/features/users/UsersPage";
import RolesPage from "@/features/roles/RolesPage";
import ProfilePage from "./ProfilePage";

export default function SettingsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "general";
  const { hasPermission } = usePermissions();
  const canViewTeam = hasPermission("users.read");
  const canManageRoles = hasPermission("users.roles");

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Manage your account and configuration" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="delivery">Delivery Log</TabsTrigger>
          <TabsTrigger value="dead-letter">Dead Letter</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          {canViewTeam && <TabsTrigger value="members">Members</TabsTrigger>}
          {canViewTeam && canManageRoles && <TabsTrigger value="roles">Roles</TabsTrigger>}
          <TabsTrigger value="profile">Profile</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="mt-4">
          <OrganizationPage embedded />
        </TabsContent>
        <TabsContent value="billing" className="mt-4">
          <BillingPage embedded />
        </TabsContent>
        <TabsContent value="channels" className="mt-4">
          <NotificationChannelsPage embedded />
        </TabsContent>
        <TabsContent value="delivery" className="mt-4">
          <DeliveryLogPage embedded />
        </TabsContent>
        <TabsContent value="dead-letter" className="mt-4">
          <DeadLetterPage embedded />
        </TabsContent>
        <TabsContent value="integrations" className="mt-4">
          <CarrierIntegrationsPage embedded />
        </TabsContent>
        {canViewTeam && (
          <TabsContent value="members" className="mt-4">
            <UsersPage embedded />
          </TabsContent>
        )}
        {canViewTeam && canManageRoles && (
          <TabsContent value="roles" className="mt-4">
            <RolesPage embedded />
          </TabsContent>
        )}
        <TabsContent value="profile" className="mt-4">
          <ProfilePage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = SettingsHubPage;
```

## Key Changes

- **Removed imports:** `NotificationsHubPage`, `TeamHubPage`
- **Added imports:** `NotificationChannelsPage`, `DeliveryLogPage`, `DeadLetterPage`, `UsersPage`, `RolesPage`
- **New tab values:** `channels`, `delivery`, `dead-letter`, `members`, `roles` (replacing `notifications`, `team`)
- **All child components already support `embedded` prop**

## Permission Handling

Two permission levels from the old TeamHubPage are preserved:

| Permission | Controls |
|-----------|----------|
| `users.read` | Members tab visibility |
| `users.roles` (AND `users.read`) | Roles tab visibility |

If a user lacks `users.read`, both Members and Roles tabs are hidden. If they have `users.read` but not `users.roles`, only Members shows.

## Tab Value Mapping (old → new)

| Old tab value | New tab value(s) |
|--------------|-----------------|
| `notifications` | `channels` (default), `delivery`, `dead-letter` |
| `team` | `members` (default), `roles` |

## Verification

- `npx tsc --noEmit` passes
- 9 tabs render with no nesting (7 visible without team permissions, up to 9 with full permissions)
- Each tab shows its embedded content directly (no inner pill tabs)
- Permission-gated tabs (Members, Roles) hide correctly when permissions are missing
- Tab switching updates `?tab=` in the URL

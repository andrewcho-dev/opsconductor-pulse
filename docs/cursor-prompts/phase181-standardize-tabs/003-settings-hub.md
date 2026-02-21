# Task 3: Settings Hub Page (Replace Left-Nav)

## Objective

Replace the Settings left-nav layout (`SettingsLayout.tsx`) with a standard tabbed hub page, matching the tab pattern used everywhere else. Delete the SettingsLayout component.

## Files to Create/Modify/Delete

- **Create:** `frontend/src/features/settings/SettingsHubPage.tsx`
- **Delete:** `frontend/src/components/layout/SettingsLayout.tsx`

## Design

The settings hub uses the standard pattern: PageHeader + `TabsList variant="line"` + `useSearchParams`.

**Tabs (6):**
| Tab value | Label | Component | Notes |
|-----------|-------|-----------|-------|
| `general` (default) | General | `OrganizationPage` | Organization settings |
| `billing` | Billing | `BillingPage` | Billing + subscription management |
| `notifications` | Notifications | `NotificationsHubPage` | Nested hub with pill tabs (Channels, Delivery, Dead Letter) |
| `integrations` | Integrations | `CarrierIntegrationsPage` | Carrier integration management |
| `team` | Team | `TeamHubPage` | Nested hub with pill tabs (Members, Roles). Permission-gated. |
| `profile` | Profile | `ProfilePage` | Personal settings |

## Implementation

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { usePermissions } from "@/services/auth";
import OrganizationPage from "./OrganizationPage";
import BillingPage from "./BillingPage";
import NotificationsHubPage from "@/features/notifications/NotificationsHubPage";
import CarrierIntegrationsPage from "./CarrierIntegrationsPage";
import TeamHubPage from "@/features/users/TeamHubPage";
import ProfilePage from "./ProfilePage";

export default function SettingsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "general";
  const { hasPermission } = usePermissions();
  const canViewTeam = hasPermission("users.read");

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Manage your account and configuration" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          {canViewTeam && <TabsTrigger value="team">Team</TabsTrigger>}
          <TabsTrigger value="profile">Profile</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="mt-4">
          <OrganizationPage embedded />
        </TabsContent>
        <TabsContent value="billing" className="mt-4">
          <BillingPage embedded />
        </TabsContent>
        <TabsContent value="notifications" className="mt-4">
          <NotificationsHubPage embedded />
        </TabsContent>
        <TabsContent value="integrations" className="mt-4">
          <CarrierIntegrationsPage embedded />
        </TabsContent>
        {canViewTeam && (
          <TabsContent value="team" className="mt-4">
            <TeamHubPage embedded />
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

## Permission Handling

The Team tab is conditionally rendered based on `users.read` permission:
- If the user has the permission: Team tab appears and is clickable
- If not: Team tab is hidden entirely. If someone navigates to `/settings?tab=team` without permission, the Tabs component won't find a matching tab and will fall back to the default behavior (showing no content for that tab value). This is acceptable — the tab simply doesn't render.

## Delete SettingsLayout

**Delete:** `frontend/src/components/layout/SettingsLayout.tsx`

This file is no longer needed. The left-nav layout is replaced by the tabbed hub. The SettingsLayout import in `router.tsx` will be removed in Task 4.

## Important Notes

- **Nested hubs:** NotificationsHubPage and TeamHubPage render with `embedded` prop, which (from Task 1) makes their internal tabs use pill variant. Visual hierarchy: outer line tabs → inner pill tabs.
- **All 6 component pages already support `embedded` prop** — they were modified in Phases 176-177 to skip their PageHeaders when embedded.
- **Route changes happen in Task 4** — this task just creates the component and deletes the layout. The router restructure is in the next task.
- **The subcategory labels** (Account, Configuration, Access Control, Personal) from the left-nav are gone. The flat tab list is simpler and consistent with every other hub page. If users need to find a specific setting, the tab labels are descriptive enough.

## Verification

- `npx tsc --noEmit` passes
- `SettingsHubPage.tsx` created at correct path
- `SettingsLayout.tsx` deleted
- Hub page renders 6 tabs (5 if Team is hidden by permissions)
- Each tab renders its embedded content without duplicate PageHeaders
- NotificationsHubPage shows pill-variant sub-tabs when inside the Settings hub
- TeamHubPage shows pill-variant sub-tabs when inside the Settings hub

# Task 4: Route Updates, CommandPalette, & UserMenu Links

## Objective

Wire DevicesHubPage and SettingsHubPage into the router, add redirects from old paths, fix the nested hub query param conflict, update CommandPalette hrefs, and update UserMenu links in AppHeader.

---

## Part 1: Fix Nested Hub Query Param Conflict (4 files)

When a hub page is rendered `embedded` inside another hub, both use `useSearchParams` to read/write `?tab=`. This creates a conflict: clicking an inner tab (e.g., "Firmware" inside Updates) would overwrite the outer hub's `tab` param, causing the outer hub to lose its selected tab.

**Fix:** When `embedded` is true, nested hubs use `useState` for tab selection instead of `useSearchParams`. This makes inner tab state local (not URL-driven), avoiding the conflict. Inner tab deep linking is intentionally lost when nested — the outer tab deep link (`/devices?tab=updates`) is sufficient.

### 1. `frontend/src/features/ota/UpdatesHubPage.tsx`

Add a `useState` import and use local state when embedded:

```tsx
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

export default function UpdatesHubPage({ embedded }: { embedded?: boolean }) {
  const [params, setParams] = useSearchParams();
  const [localTab, setLocalTab] = useState("campaigns");

  const tab = embedded ? localTab : (params.get("tab") ?? "campaigns");
  const onTabChange = (v: string) => {
    if (embedded) {
      setLocalTab(v);
    } else {
      setParams({ tab: v }, { replace: true });
    }
  };

  return (
    <div className="space-y-4">
      {!embedded && <PageHeader title="Updates" description="Manage firmware and OTA rollouts" />}
      <Tabs value={tab} onValueChange={onTabChange}>
        <TabsList variant={embedded ? "default" : "line"}>
          ...
        </TabsList>
        ...
      </Tabs>
    </div>
  );
}
```

### 2. `frontend/src/features/fleet/ToolsHubPage.tsx`

Same pattern — add `useState`, use local state when embedded. Default tab should match whatever the current default is (likely `"guide"`).

### 3. `frontend/src/features/notifications/NotificationsHubPage.tsx`

Same pattern. Default inner tab is `"channels"`.

### 4. `frontend/src/features/users/TeamHubPage.tsx`

Same pattern. Default inner tab is `"members"`.

---

## Part 2: Restructure Router

**Modify:** `frontend/src/app/router.tsx`

### Import Changes

**Add imports:**
```tsx
import DevicesHubPage from "@/features/devices/DevicesHubPage";
import SettingsHubPage from "@/features/settings/SettingsHubPage";
```

**Remove imports** (these are now imported internally by the hub pages, not the router):
```tsx
// DELETE these import lines:
import SettingsLayout from "@/components/layout/SettingsLayout";
import UpdatesHubPage from "@/features/ota/UpdatesHubPage";
import ToolsHubPage from "@/features/fleet/ToolsHubPage";
import NotificationsHubPage from "@/features/notifications/NotificationsHubPage";
import TeamHubPage from "@/features/users/TeamHubPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import SitesPage from "@/features/sites/SitesPage";
import TemplateListPage from "@/features/templates/TemplateListPage";
import FleetMapPage from "@/features/map/FleetMapPage";
import OrganizationPage from "@/features/settings/OrganizationPage";
import BillingPage from "@/features/settings/BillingPage";
import CarrierIntegrationsPage from "@/features/settings/CarrierIntegrationsPage";
import ProfilePage from "@/features/settings/ProfilePage";
```

**Also remove** the `RequirePermission` function and its `usePermissions` import — it was only used for the `settings/access` route, which is now handled internally by SettingsHubPage's conditional Team tab rendering. (Keep `useAuth` — it's still used by `HomeRedirect`, `RequireOperator`, `RequireCustomer`.)

### Route Structure

Replace the entire customer children array with this structure. **Keep all routes that are unchanged** (home, dashboard, alerts, analytics, rules, devices/import, devices/wizard, devices/:deviceId, sensors, fleet/getting-started, activity-log, metrics, jobs, ota/campaigns/:campaignId, subscription/renew, alert-rules redirect, escalation-policies redirect, oncall redirect, maintenance-windows redirect).

**Key changes:**

1. **Replace** `{ path: "devices", element: <DeviceListPage /> }` with:
```tsx
{ path: "devices", element: <DevicesHubPage /> },
```

2. **Replace** the settings block (lines 142-163):
```tsx
// OLD — DELETE this entire block:
{
  path: "settings",
  element: <SettingsLayout />,
  children: [
    { index: true, element: <Navigate to="/settings/general" replace /> },
    { path: "general", element: <OrganizationPage embedded /> },
    ...
  ],
},

// NEW — replace with:
{ path: "settings", element: <SettingsHubPage /> },
```

3. **Replace** standalone routes that are now hub tabs:
```tsx
// OLD:
{ path: "updates", element: <UpdatesHubPage /> },
{ path: "fleet/tools", element: <ToolsHubPage /> },
{ path: "sites", element: <SitesPage /> },
{ path: "device-groups", element: <DeviceGroupsPage /> },
{ path: "map", element: <FleetMapPage /> },

// NEW — redirects to devices hub tabs:
{ path: "sites", element: <Navigate to="/devices?tab=sites" replace /> },
{ path: "templates", element: <Navigate to="/devices?tab=templates" replace /> },
{ path: "device-groups", element: <Navigate to="/devices?tab=groups" replace /> },
{ path: "map", element: <Navigate to="/devices?tab=map" replace /> },
{ path: "updates", element: <Navigate to="/devices?tab=updates" replace /> },
{ path: "fleet/tools", element: <Navigate to="/devices?tab=tools" replace /> },
```

4. **Add** redirects from old settings sub-paths:
```tsx
{ path: "settings/general", element: <Navigate to="/settings?tab=general" replace /> },
{ path: "settings/billing", element: <Navigate to="/settings?tab=billing" replace /> },
{ path: "settings/notifications", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "settings/integrations", element: <Navigate to="/settings?tab=integrations" replace /> },
{ path: "settings/access", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "settings/profile", element: <Navigate to="/settings?tab=profile" replace /> },
{ path: "settings/organization", element: <Navigate to="/settings?tab=general" replace /> },
{ path: "settings/carrier", element: <Navigate to="/settings?tab=integrations" replace /> },
```

5. **Update** existing redirect targets that pointed to old settings paths:
```tsx
// These already exist — update their targets:
{ path: "notifications", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "billing", element: <Navigate to="/settings?tab=billing" replace /> },
{ path: "team", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "users", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "roles", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "subscription", element: <Navigate to="/settings?tab=billing" replace /> },
{ path: "delivery-log", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "dead-letter", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "integrations", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "integrations/*", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "customer/integrations", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "customer/integrations/*", element: <Navigate to="/settings?tab=notifications" replace /> },
```

6. **Update** OTA redirect targets:
```tsx
{ path: "ota/campaigns", element: <Navigate to="/devices?tab=updates" replace /> },
{ path: "ota/firmware", element: <Navigate to="/devices?tab=updates" replace /> },
```

7. **Keep** these detail routes unchanged — they still need their own pages:
```tsx
{ path: "sites/:siteId", element: <SiteDetailPage /> },
{ path: "templates/:templateId", element: <TemplateDetailPage /> },
{ path: "devices/:deviceId", element: <DeviceDetailPage /> },
{ path: "devices/import", element: <BulkImportPage /> },
{ path: "devices/wizard", element: <SetupWizard /> },
{ path: "device-groups/:groupId", element: <DeviceGroupsPage /> },
{ path: "ota/campaigns/:campaignId", element: <OtaCampaignDetailPage /> },
```

8. **Keep** `{ path: "fleet/getting-started", element: <GettingStartedPage /> }` — it's a standalone page, not a tab.

### Note on `templates` Route

The current router has `{ path: "templates", element: <TemplateListPage /> }` but no redirect. In the new structure, `/templates` becomes a redirect to `/devices?tab=templates`. The `TemplateListPage` import can be removed from the router since it's now imported by `DevicesHubPage` internally. The `TemplateDetailPage` import stays (for `/templates/:templateId`).

---

## Part 3: Update CommandPalette

**Modify:** `frontend/src/components/shared/CommandPalette.tsx`

Update the `pages` array hrefs. Replace the current array entries with updated paths:

```tsx
const pages = useMemo(
  () => [
    { label: "Home", href: "/home", icon: Home },
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Devices", href: "/devices", icon: Cpu },
    { label: "Sites", href: "/devices?tab=sites", icon: Building2 },
    { label: "Templates", href: "/devices?tab=templates", icon: LayoutDashboard },
    { label: "Fleet Map", href: "/devices?tab=map", icon: Layers },
    { label: "Device Groups", href: "/devices?tab=groups", icon: Layers },
    { label: "Updates", href: "/devices?tab=updates", icon: Activity },
    { label: "Tools", href: "/devices?tab=tools", icon: Wrench },
    { label: "Connection Guide", href: "/devices?tab=tools", icon: Wrench },
    { label: "MQTT Test Client", href: "/devices?tab=tools", icon: Wrench },
    { label: "Alerts", href: "/alerts", icon: Bell },
    { label: "Rules", href: "/rules", icon: Scale },
    { label: "Alert Rules", href: "/rules?tab=alert-rules", icon: Scale },
    { label: "Escalation Policies", href: "/rules?tab=escalation", icon: Scale },
    { label: "On-Call Schedules", href: "/rules?tab=oncall", icon: Scale },
    { label: "Maintenance Windows", href: "/rules?tab=maintenance", icon: Scale },
    { label: "Analytics", href: "/analytics", icon: Gauge },
    { label: "Settings", href: "/settings", icon: Settings },
    { label: "General Settings", href: "/settings?tab=general", icon: Building2 },
    { label: "Billing", href: "/settings?tab=billing", icon: CreditCard },
    { label: "Notifications", href: "/settings?tab=notifications", icon: Webhook },
    { label: "Integrations", href: "/settings?tab=integrations", icon: Radio },
    { label: "Team", href: "/settings?tab=team", icon: Users },
    { label: "Profile", href: "/settings?tab=profile", icon: Users },
    { label: "Getting Started", href: "/fleet/getting-started", icon: Activity },
  ],
  []
);
```

**Changes from current:**
- `Sites`: `/sites` → `/devices?tab=sites`
- `Templates`: `/templates` → `/devices?tab=templates`
- `Fleet Map`: `/map` → `/devices?tab=map`
- `Device Groups`: `/device-groups` → `/devices?tab=groups`
- `Updates`: `/updates` → `/devices?tab=updates`
- `Tools`: `/fleet/tools` → `/devices?tab=tools`
- `Connection Guide`: `/fleet/tools?tab=guide` → `/devices?tab=tools` (inner tab deep link lost when nested)
- `MQTT Test Client`: `/fleet/tools?tab=mqtt` → `/devices?tab=tools`
- `Notifications`: `/settings/notifications` → `/settings?tab=notifications`
- `Integrations`: `/settings/integrations` → `/settings?tab=integrations`
- `Billing`: `/settings/billing` → `/settings?tab=billing`
- `Profile`: `/settings/profile` → `/settings?tab=profile`
- `Organization` → renamed to `General Settings`: `/settings/general` → `/settings?tab=general`
- `Team`: `/settings/access` → `/settings?tab=team`

---

## Part 4: Update AppHeader UserMenu Links

**Modify:** `frontend/src/components/layout/AppHeader.tsx`

In the `UserMenu` component, update the two `<Link>` targets:

```tsx
// OLD:
<Link to="/settings/profile">
// NEW:
<Link to="/settings?tab=profile">

// OLD:
<Link to="/settings/organization">
// NEW:
<Link to="/settings?tab=general">
```

No other changes needed in AppHeader. The breadcrumb `labelMap` is harmless as-is — entries for URL segments that no longer appear in paths (like `access`, `general`, `profile`) simply won't match and won't cause issues.

---

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Router compiles with no errors
- No unused imports remain (SettingsLayout, DeviceListPage, SitesPage, TemplateListPage, FleetMapPage, UpdatesHubPage, ToolsHubPage, NotificationsHubPage, TeamHubPage, OrganizationPage, BillingPage, CarrierIntegrationsPage, ProfilePage are all removed)
- `/devices` renders DevicesHubPage (not DeviceListPage)
- `/settings` renders SettingsHubPage (not SettingsLayout)
- `/sites` redirects to `/devices?tab=sites`
- `/templates` redirects to `/devices?tab=templates`
- `/settings/general` redirects to `/settings?tab=general`
- `/settings/access` redirects to `/settings?tab=team`
- `/billing` redirects to `/settings?tab=billing`
- Detail routes still work: `/devices/:deviceId`, `/templates/:templateId`, `/sites/:siteId`, `/device-groups/:groupId`, `/ota/campaigns/:campaignId`
- Nested hub tabs work: clicking "Firmware" inside Updates tab doesn't break the outer Devices tab
- CommandPalette navigates to correct hub tab URLs
- UserMenu Profile/Organization links navigate to correct settings tabs

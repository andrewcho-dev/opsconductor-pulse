# Task 4: Route Updates — Settings Routes + Redirects

## Objective

Restructure the router to nest all settings-related routes under a `SettingsLayout` component at `/settings/`. Add redirects from old routes. Update the CommandPalette page list.

## File to Modify

`frontend/src/app/router.tsx`

---

## Changes

### 1. Add SettingsLayout import

```tsx
import SettingsLayout from "@/components/layout/SettingsLayout";
```

### 2. Restructure settings routes

Remove the standalone settings-related routes from the `RequireCustomer` children:

**Remove these individual routes:**
```tsx
{ path: "notifications", element: <NotificationsHubPage /> },
{ path: "settings/profile", element: <ProfilePage /> },
{ path: "settings/organization", element: <OrganizationPage /> },
{ path: "settings/carrier", element: <CarrierIntegrationsPage /> },
{ path: "billing", element: <BillingPage /> },
```

**Remove the standalone Team permission block:**
```tsx
{
  element: <RequirePermission permission="users.read" />,
  children: [
    { path: "team", element: <TeamHubPage /> },
    { path: "users", element: <Navigate to="/team" replace /> },
    { path: "roles", element: <Navigate to="/team?tab=roles" replace /> },
  ],
},
```

**Add a nested `settings` route with SettingsLayout:**

Place this inside the `RequireCustomer` children array:

```tsx
{
  path: "settings",
  element: <SettingsLayout />,
  children: [
    { index: true, element: <Navigate to="/settings/general" replace /> },
    { path: "general", element: <OrganizationPage embedded /> },
    { path: "billing", element: <BillingPage embedded /> },
    { path: "notifications", element: <NotificationsHubPage embedded /> },
    { path: "integrations", element: <CarrierIntegrationsPage embedded /> },
    {
      path: "access",
      element: (
        <RequirePermission permission="users.read">
          <TeamHubPage embedded />
        </RequirePermission>
      ),
    },
    { path: "profile", element: <ProfilePage embedded /> },
  ],
},
```

**Note on RequirePermission for Access Control:** The `RequirePermission` wrapper ensures that navigating to `/settings/access` without `users.read` redirects to `/dashboard`. The SettingsLayout's left-nav also hides the "Team" link based on the same permission check.

### 3. Add redirects from old routes

Add these redirects inside the `RequireCustomer` children (alongside other existing redirects):

```tsx
// Settings route redirects (Phase 177)
{ path: "notifications", element: <Navigate to="/settings/notifications" replace /> },
{ path: "billing", element: <Navigate to="/settings/billing" replace /> },
{ path: "team", element: <Navigate to="/settings/access" replace /> },
{ path: "users", element: <Navigate to="/settings/access" replace /> },
{ path: "roles", element: <Navigate to="/settings/access?tab=roles" replace /> },
```

**Update existing redirects** that pointed to `/notifications` to now point to `/settings/notifications`:

```tsx
// Update these Phase 176 redirects:
{ path: "delivery-log", element: <Navigate to="/settings/notifications?tab=delivery" replace /> },
{ path: "dead-letter", element: <Navigate to="/settings/notifications?tab=dead-letter" replace /> },
{ path: "integrations", element: <Navigate to="/settings/notifications" replace /> },
{ path: "integrations/*", element: <Navigate to="/settings/notifications" replace /> },
{ path: "customer/integrations", element: <Navigate to="/settings/notifications" replace /> },
{ path: "customer/integrations/*", element: <Navigate to="/settings/notifications" replace /> },
```

**Update the subscription redirect:**
```tsx
{ path: "subscription", element: <Navigate to="/settings/billing" replace /> },
```

**Keep the old `/settings/organization` and `/settings/carrier` paths working:**
```tsx
{ path: "settings/organization", element: <Navigate to="/settings/general" replace /> },
{ path: "settings/carrier", element: <Navigate to="/settings/integrations" replace /> },
```

Wait — these are under the `settings` nested route already. The `settings/organization` path would be relative to the `/settings` parent, making it `/settings/settings/organization`. That's wrong.

**Better approach:** Add the old `/settings/*` redirects as flat routes in the `RequireCustomer` children, BEFORE the nested `settings` route block. Or, within the `settings` children, add:

```tsx
// Inside the settings children:
{ path: "organization", element: <Navigate to="/settings/general" replace /> },
{ path: "carrier", element: <Navigate to="/settings/integrations" replace /> },
```

This maps `/settings/organization` → `/settings/general` and `/settings/carrier` → `/settings/integrations`. The `/settings/profile` path already works (it's a direct child route).

### 4. Clean up unused imports

Remove imports that are no longer directly used in the router (they're now imported by SettingsLayout or hub pages):

Check which of these are still referenced directly in the router vs. only indirectly through SettingsLayout:
- `NotificationsHubPage` — now only rendered inside SettingsLayout. But it's passed as `element: <NotificationsHubPage embedded />` in the settings children, so the import IS still needed in router.tsx.
- `TeamHubPage` — same, still needed.
- `ProfilePage`, `OrganizationPage`, `BillingPage`, `CarrierIntegrationsPage` — same, still needed.

Actually, all these imports are still needed because the router directly references them as JSX elements. No imports to remove here.

### 5. Update CommandPalette page list

**File:** `frontend/src/components/shared/CommandPalette.tsx`

Update the `pages` array entries for settings pages:

- Update "Notifications" href from `/notifications` to `/settings/notifications`
- Update "Team" href from `/team` to `/settings/access`
- Update "Billing" href from `/billing` to `/settings/billing`
- Update "Integrations" or "Carrier Integrations" href from `/settings/carrier` to `/settings/integrations`
- Update "Profile" href to `/settings/profile` (may already be correct)
- Update "Organization" href to `/settings/general`
- Add "Settings" entry with href `/settings` if not already present

### 6. Update AppHeader breadcrumb labelMap

**File:** `frontend/src/components/layout/AppHeader.tsx`

The `labelMap` in `useBreadcrumbs()` needs entries for the new settings sub-paths:

```tsx
const labelMap: Record<string, string> = {
  // ... existing entries ...
  settings: "Settings",
  general: "General",
  access: "Access Control",
  // Keep existing: notifications, integrations, profile, billing
};
```

Verify that existing entries like `notifications`, `billing`, `profile` are already in the labelMap (they should be from previous phases).

## Verification

- `npx tsc --noEmit` passes
- `/settings` redirects to `/settings/general`
- `/settings/general` shows Organization settings (embedded, no PageHeader)
- `/settings/notifications` shows Notifications hub with Channels/Delivery/Dead Letter tabs
- `/settings/access` shows Team hub with Members/Roles tabs (only for users with `users.read` permission)
- `/settings/billing` shows Billing page
- `/settings/integrations` shows Carrier Integrations page
- `/settings/profile` shows Profile page
- Old routes redirect correctly:
  - `/notifications` → `/settings/notifications`
  - `/billing` → `/settings/billing`
  - `/team` → `/settings/access`
  - `/users` → `/settings/access`
  - `/roles` → `/settings/access?tab=roles`
  - `/delivery-log` → `/settings/notifications?tab=delivery`
  - `/subscription` → `/settings/billing`
  - `/settings/organization` → `/settings/general`
  - `/settings/carrier` → `/settings/integrations`
- Breadcrumbs show correct labels: Settings > General, Settings > Notifications, etc.
- CommandPalette search finds all settings pages with correct paths

# Task 8: Route Updates + Redirects

## Objective

Update `router.tsx` to register the new Home page and hub page routes, add redirects from old standalone routes, and update the `HomeRedirect` to point to `/home`.

## File to Modify

`frontend/src/app/router.tsx`

---

## Changes

### 1. Add imports for new pages

Add these imports at the top of the file:

```tsx
import HomePage from "@/features/home/HomePage";
import AlertsHubPage from "@/features/alerts/AlertsHubPage";
import AnalyticsHubPage from "@/features/analytics/AnalyticsHubPage";
import UpdatesHubPage from "@/features/ota/UpdatesHubPage";
import NotificationsHubPage from "@/features/notifications/NotificationsHubPage";
import TeamHubPage from "@/features/users/TeamHubPage";
```

### 2. Remove imports for pages that are now only rendered as hub tabs

These imports can be removed from the top-level router since the hub pages import them directly:

```tsx
// REMOVE these imports (they're now imported by hub pages, not the router):
// import AlertRulesPage from "@/features/alerts/AlertRulesPage";
// import MaintenanceWindowsPage from "@/features/alerts/MaintenanceWindowsPage";
// import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
// import OncallSchedulesPage from "@/features/oncall/OncallSchedulesPage";
// import ReportsPage from "@/features/reports/ReportsPage";
// import FirmwareListPage from "@/features/ota/FirmwareListPage";
// import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
// import DeadLetterPage from "@/features/messaging/DeadLetterPage";
// import SubscriptionPage from "@/features/subscription/SubscriptionPage";
```

**Keep** these imports since they're still used directly:
- `AlertListPage` — no, wait, the hub imports this. But the redirect for `/alerts` points to `AlertsHubPage`. So `AlertListPage` import can be removed from router too.
- `OtaCampaignsPage` — the hub imports this, so remove from router. But `OtaCampaignDetailPage` is still a direct route — keep its import.
- `NotificationChannelsPage` — the hub imports this, remove from router.
- `UsersPage` — the hub imports this, remove from router.
- `RolesPage` — the hub imports this, remove from router.
- `AnalyticsPage` — the hub imports this, remove from router.

**Keep** all detail page imports (DeviceDetailPage, SiteDetailPage, TemplateDetailPage, OtaCampaignDetailPage, etc.) since those are still direct routes.

### 3. Update HomeRedirect

Change the customer redirect from `/dashboard` to `/home`:

```tsx
function HomeRedirect() {
  const { isOperator } = useAuth();
  return <Navigate to={isOperator ? "/operator" : "/home"} replace />;
}
```

### 4. Update customer route children

Replace the current flat list of customer routes with the new hub-based structure. The key changes:

**Add new routes:**
```tsx
{ path: "home", element: <HomePage /> },
{ path: "alerts", element: <AlertsHubPage /> },
{ path: "analytics", element: <AnalyticsHubPage /> },
{ path: "updates", element: <UpdatesHubPage /> },
{ path: "notifications", element: <NotificationsHubPage /> },
```

**Keep these routes unchanged:**
```tsx
{ path: "dashboard", element: <DashboardPage /> },
{ path: "fleet/getting-started", element: <GettingStartedPage /> },
{ path: "sites", element: <SitesPage /> },
{ path: "sites/:siteId", element: <SiteDetailPage /> },
{ path: "templates", element: <TemplateListPage /> },
{ path: "templates/:templateId", element: <TemplateDetailPage /> },
{ path: "devices", element: <DeviceListPage /> },
{ path: "devices/import", element: <BulkImportPage /> },
{ path: "devices/wizard", element: <SetupWizard /> },
{ path: "devices/:deviceId", element: <DeviceDetailPage /> },
{ path: "sensors", element: <SensorListPage /> },
{ path: "device-groups", element: <DeviceGroupsPage /> },
{ path: "device-groups/:groupId", element: <DeviceGroupsPage /> },
{ path: "map", element: <FleetMapPage /> },
{ path: "ota/campaigns/:campaignId", element: <OtaCampaignDetailPage /> },
{ path: "activity-log", element: <ActivityLogPage /> },
{ path: "metrics", element: <MetricsPage /> },
{ path: "jobs", element: <JobsPage /> },
{ path: "subscription/renew", element: <RenewalPage /> },
{ path: "settings/profile", element: <ProfilePage /> },
{ path: "settings/organization", element: <OrganizationPage /> },
{ path: "settings/carrier", element: <CarrierIntegrationsPage /> },
{ path: "billing", element: <BillingPage /> },
```

**Add redirects from old routes to hub pages:**
```tsx
// Alerts hub redirects
{ path: "alert-rules", element: <Navigate to="/alerts?tab=rules" replace /> },
{ path: "escalation-policies", element: <Navigate to="/alerts?tab=escalation" replace /> },
{ path: "oncall", element: <Navigate to="/alerts?tab=oncall" replace /> },
{ path: "maintenance-windows", element: <Navigate to="/alerts?tab=maintenance" replace /> },

// Analytics hub redirects
{ path: "reports", element: <Navigate to="/analytics?tab=reports" replace /> },

// Updates hub redirects
{ path: "ota/campaigns", element: <Navigate to="/updates?tab=campaigns" replace /> },
{ path: "ota/firmware", element: <Navigate to="/updates?tab=firmware" replace /> },

// Notifications hub redirects
{ path: "delivery-log", element: <Navigate to="/notifications?tab=delivery" replace /> },
{ path: "dead-letter", element: <Navigate to="/notifications?tab=dead-letter" replace /> },

// Billing redirect (Subscription → Billing)
{ path: "subscription", element: <Navigate to="/billing" replace /> },

// Keep existing integration redirects
{ path: "integrations", element: <Navigate to="/notifications" replace /> },
{ path: "integrations/*", element: <Navigate to="/notifications" replace /> },
{ path: "customer/integrations", element: <Navigate to="/notifications" replace /> },
{ path: "customer/integrations/*", element: <Navigate to="/notifications" replace /> },
```

### 5. Update Team hub route

Replace the separate `users` and `roles` permission-gated routes with a single Team hub route:

**Remove:**
```tsx
{
  element: <RequirePermission permission="users.read" />,
  children: [{ path: "users", element: <UsersPage /> }],
},
{
  element: <RequirePermission permission="users.roles" />,
  children: [{ path: "roles", element: <RolesPage /> }],
},
```

**Replace with:**
```tsx
{
  element: <RequirePermission permission="users.read" />,
  children: [
    { path: "team", element: <TeamHubPage /> },
    // Redirects from old routes
    { path: "users", element: <Navigate to="/team" replace /> },
    { path: "roles", element: <Navigate to="/team?tab=roles" replace /> },
  ],
},
```

This keeps the permission guard on the `/team` route and adds redirects from the old paths.

### 6. Update CommandPalette pages list

**File:** `frontend/src/components/shared/CommandPalette.tsx`

Update the `pages` array to reflect the new navigation. Replace entries for consolidated pages with their hub equivalents:

- Replace "Alert Rules" (`/alert-rules`) with just "Alerts" (`/alerts`)
- Remove standalone "Escalation Policies", "On-Call", "Maintenance Windows" (they're tabs now)
- Replace "OTA Campaigns" + "Firmware" with "Updates" (`/updates`)
- Remove standalone "Delivery Log", "Dead Letter Queue" (they're tabs now)
- Replace "Users" with "Team" (`/team`)
- Remove standalone "Roles" (it's a tab now)
- Remove "Subscription" (merged into Billing)
- Add "Home" (`/home`)

Add the `Home` icon to the lucide import in CommandPalette.

## Verification

- `npx tsc --noEmit` passes
- `/` redirects to `/home` for customers, `/operator` for operators
- `/home` renders the Home page
- `/alerts` renders AlertsHubPage (not AlertListPage directly)
- `/alerts?tab=rules` shows the Rules tab
- `/alert-rules` redirects to `/alerts?tab=rules`
- `/analytics` renders AnalyticsHubPage
- `/reports` redirects to `/analytics?tab=reports`
- `/updates` renders UpdatesHubPage
- `/ota/campaigns` redirects to `/updates?tab=campaigns`
- `/ota/campaigns/:id` still renders the campaign detail page directly
- `/notifications` renders NotificationsHubPage
- `/delivery-log` redirects to `/notifications?tab=delivery`
- `/team` renders TeamHubPage (behind users.read permission)
- `/users` redirects to `/team`
- `/subscription` redirects to `/billing`
- `/subscription/renew` still works directly
- All operator routes unchanged
- CommandPalette search reflects the new page structure

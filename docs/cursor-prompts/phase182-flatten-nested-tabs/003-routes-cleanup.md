# Task 3: Update Routes, CommandPalette, Delete Unused Hub Pages

## Objective

Update redirect targets in the router and CommandPalette to match the new flat tab values, and delete the 4 nested hub pages that are now dead code.

---

## Part 1: Delete Unused Hub Pages

These files are no longer imported anywhere — their child components are now imported directly by DevicesHubPage and SettingsHubPage.

**Delete these 4 files:**
- `frontend/src/features/ota/UpdatesHubPage.tsx`
- `frontend/src/features/fleet/ToolsHubPage.tsx`
- `frontend/src/features/notifications/NotificationsHubPage.tsx`
- `frontend/src/features/users/TeamHubPage.tsx`

---

## Part 2: Update Router Redirects

**Modify:** `frontend/src/app/router.tsx`

Update redirect targets that reference the old nested tab values (`updates`, `tools`, `notifications`, `team`). The tab values changed when we flattened:

### Devices hub redirects (old → new tab values)

```tsx
// OLD:
{ path: "updates", element: <Navigate to="/devices?tab=updates" replace /> },
{ path: "fleet/tools", element: <Navigate to="/devices?tab=tools" replace /> },
{ path: "ota/campaigns", element: <Navigate to="/devices?tab=updates" replace /> },
{ path: "ota/firmware", element: <Navigate to="/devices?tab=updates" replace /> },

// NEW:
{ path: "updates", element: <Navigate to="/devices?tab=campaigns" replace /> },
{ path: "fleet/tools", element: <Navigate to="/devices?tab=guide" replace /> },
{ path: "ota/campaigns", element: <Navigate to="/devices?tab=campaigns" replace /> },
{ path: "ota/firmware", element: <Navigate to="/devices?tab=firmware" replace /> },
```

### Settings hub redirects (old → new tab values)

```tsx
// OLD:
{ path: "settings/notifications", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "settings/access", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "notifications", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "delivery-log", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "dead-letter", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "team", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "users", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "roles", element: <Navigate to="/settings?tab=team" replace /> },
{ path: "integrations", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "integrations/*", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "customer/integrations", element: <Navigate to="/settings?tab=notifications" replace /> },
{ path: "customer/integrations/*", element: <Navigate to="/settings?tab=notifications" replace /> },

// NEW:
{ path: "settings/notifications", element: <Navigate to="/settings?tab=channels" replace /> },
{ path: "settings/access", element: <Navigate to="/settings?tab=members" replace /> },
{ path: "notifications", element: <Navigate to="/settings?tab=channels" replace /> },
{ path: "delivery-log", element: <Navigate to="/settings?tab=delivery" replace /> },
{ path: "dead-letter", element: <Navigate to="/settings?tab=dead-letter" replace /> },
{ path: "team", element: <Navigate to="/settings?tab=members" replace /> },
{ path: "users", element: <Navigate to="/settings?tab=members" replace /> },
{ path: "roles", element: <Navigate to="/settings?tab=roles" replace /> },
{ path: "integrations", element: <Navigate to="/settings?tab=channels" replace /> },
{ path: "integrations/*", element: <Navigate to="/settings?tab=channels" replace /> },
{ path: "customer/integrations", element: <Navigate to="/settings?tab=channels" replace /> },
{ path: "customer/integrations/*", element: <Navigate to="/settings?tab=channels" replace /> },
```

### Redirects that stay unchanged

These already point to tab values that didn't change:

```tsx
{ path: "sites", element: <Navigate to="/devices?tab=sites" replace /> },          // unchanged
{ path: "templates", element: <Navigate to="/devices?tab=templates" replace /> },    // unchanged
{ path: "device-groups", element: <Navigate to="/devices?tab=groups" replace /> },   // unchanged
{ path: "map", element: <Navigate to="/devices?tab=map" replace /> },                // unchanged
{ path: "settings/general", element: <Navigate to="/settings?tab=general" replace /> },      // unchanged
{ path: "settings/billing", element: <Navigate to="/settings?tab=billing" replace /> },      // unchanged
{ path: "settings/integrations", element: <Navigate to="/settings?tab=integrations" replace /> }, // unchanged
{ path: "settings/profile", element: <Navigate to="/settings?tab=profile" replace /> },      // unchanged
{ path: "billing", element: <Navigate to="/settings?tab=billing" replace /> },               // unchanged
{ path: "subscription", element: <Navigate to="/settings?tab=billing" replace /> },          // unchanged
```

---

## Part 3: Update CommandPalette

**Modify:** `frontend/src/components/shared/CommandPalette.tsx`

Update the `pages` array to reflect the new flat tab values:

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
    { label: "Campaigns", href: "/devices?tab=campaigns", icon: Activity },
    { label: "Firmware", href: "/devices?tab=firmware", icon: Activity },
    { label: "Connection Guide", href: "/devices?tab=guide", icon: Wrench },
    { label: "MQTT Test Client", href: "/devices?tab=mqtt", icon: Wrench },
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
    { label: "Channels", href: "/settings?tab=channels", icon: Webhook },
    { label: "Delivery Log", href: "/settings?tab=delivery", icon: Webhook },
    { label: "Dead Letter", href: "/settings?tab=dead-letter", icon: Webhook },
    { label: "Integrations", href: "/settings?tab=integrations", icon: Radio },
    { label: "Members", href: "/settings?tab=members", icon: Users },
    { label: "Roles", href: "/settings?tab=roles", icon: Users },
    { label: "Profile", href: "/settings?tab=profile", icon: Users },
    { label: "Getting Started", href: "/fleet/getting-started", icon: Activity },
  ],
  []
);
```

**Changes from current:**

| Old entry | New entry |
|-----------|-----------|
| `Updates` → `/devices?tab=updates` | `Campaigns` → `/devices?tab=campaigns` |
| `Tools` → `/devices?tab=tools` | Removed (replaced by Guide and MQTT entries) |
| `Connection Guide` → `/devices?tab=tools` | `Connection Guide` → `/devices?tab=guide` |
| `MQTT Test Client` → `/devices?tab=tools` | `MQTT Test Client` → `/devices?tab=mqtt` |
| `Notifications` → `/settings?tab=notifications` | `Channels` → `/settings?tab=channels` |
| `Team` → `/settings?tab=team` | `Members` → `/settings?tab=members` |
| — | **Added:** `Firmware` → `/devices?tab=firmware` |
| — | **Added:** `Delivery Log` → `/settings?tab=delivery` |
| — | **Added:** `Dead Letter` → `/settings?tab=dead-letter` |
| — | **Added:** `Roles` → `/settings?tab=roles` |

---

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- No TypeScript errors (no references to deleted hub pages remain)
- 4 hub page files are deleted
- `/updates` redirects to `/devices?tab=campaigns` (not `?tab=updates`)
- `/fleet/tools` redirects to `/devices?tab=guide` (not `?tab=tools`)
- `/ota/firmware` redirects to `/devices?tab=firmware` (not `?tab=updates`)
- `/notifications` redirects to `/settings?tab=channels` (not `?tab=notifications`)
- `/delivery-log` redirects to `/settings?tab=delivery` (not `?tab=notifications`)
- `/dead-letter` redirects to `/settings?tab=dead-letter` (not `?tab=notifications`)
- `/team` redirects to `/settings?tab=members` (not `?tab=team`)
- `/roles` redirects to `/settings?tab=roles` (not `?tab=team`)
- CommandPalette entries navigate to correct flat tab URLs
- Every searchable page in CommandPalette deep-links directly to its tab (no intermediate nesting)

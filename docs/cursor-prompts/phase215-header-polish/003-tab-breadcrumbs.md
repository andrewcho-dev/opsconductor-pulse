# Task 3: Show Active Tab in Breadcrumb Trail

## File
`frontend/src/components/layout/AppHeader.tsx`

## Problem
`useBreadcrumbs()` only reads `location.pathname`. When a user is on
`/settings?tab=profile`, the breadcrumb shows only "Settings" with no
indication of which tab is active.

## Expected Behaviour
- `/settings?tab=profile`  → Settings › Profile
- `/settings?tab=general`  → Settings › General
- `/settings?tab=access`   → Settings › Access Control
- `/devices/abc123?tab=sensors` → Devices › abc123 › Sensors
- `/settings` (no tab)     → Settings  (unchanged)

## Implementation
Replace the entire `useBreadcrumbs` function with this updated version:

```tsx
function useBreadcrumbs(): { label: string; href?: string }[] {
  const location = useLocation();
  const parts = location.pathname.split("/").filter(Boolean);

  const labelMap: Record<string, string> = {
    dashboard: "Dashboard",
    devices: "Devices",
    sites: "Sites",
    templates: "Templates",
    map: "Fleet Map",
    "device-groups": "Device Groups",
    alerts: "Alerts",
    rules: "Rules",
    "alert-rules": "Alert Rules",
    "escalation-policies": "Escalation Policies",
    oncall: "On-Call",
    "maintenance-windows": "Maintenance Windows",
    notifications: "Notifications",
    "delivery-log": "Delivery Log",
    "dead-letter": "Dead Letter",
    analytics: "Analytics",
    reports: "Reports",
    subscription: "Subscription",
    billing: "Billing",
    settings: "Settings",
    general: "General",
    access: "Access Control",
    integrations: "Integrations",
    users: "Team",
    roles: "Roles",
    ota: "OTA",
    fleet: "Fleet",
    tools: "Tools",
    operator: "Operator",
    "getting-started": "Getting Started",
    campaigns: "Campaigns",
    firmware: "Firmware",
    profile: "Profile",
    organization: "Organization",
    carrier: "Carrier Integrations",
    import: "Import",
    wizard: "Wizard",
    // tab-specific labels
    overview: "Overview",
    sensors: "Sensors",
    telemetry: "Telemetry",
    commands: "Commands",
    certificates: "Certificates",
    uptime: "Uptime",
    config: "Configuration",
    security: "Security",
    members: "Members",
    webhooks: "Webhooks",
    noc: "NOC",
    tenants: "Tenants",
    subscriptions: "Subscriptions",
    support: "Support",
  };

  const crumbs: { label: string; href?: string }[] = [];
  let path = "";
  for (const part of parts) {
    path += `/${part}`;
    const label = labelMap[part];
    if (label) {
      crumbs.push({ label, href: path });
    } else if (/^[0-9a-f-]{8,}$/i.test(part) || /^\d+$/.test(part)) {
      crumbs.push({ label: part.length > 12 ? `${part.slice(0, 8)}...` : part });
    }
  }

  // Append active tab as terminal crumb if ?tab= is present
  const tab = new URLSearchParams(location.search).get("tab");
  if (tab) {
    const tabLabel = labelMap[tab] ?? tab.charAt(0).toUpperCase() + tab.slice(1);
    // Last path crumb becomes a link (it's now a navigable parent)
    // Tab crumb becomes the terminal (no href)
    crumbs.push({ label: tabLabel });
  } else {
    // No tab — strip href from last crumb (current page, not navigable)
    if (crumbs.length > 0) {
      delete crumbs[crumbs.length - 1].href;
    }
  }

  return crumbs;
}
```

## Key Logic
- When `?tab=profile` is present: "Settings" keeps its href (`/settings`),
  "Profile" is appended with no href (terminal crumb, not a link).
- When no tab: last path crumb loses its href as before.
- Unknown tab values fall back to capitalising the raw tab string.

## Verification
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Confirm clean. Then manually test in browser:
- Navigate to /settings?tab=profile → breadcrumb shows: Settings › Profile
- Navigate to /settings (no tab) → breadcrumb shows: Settings
- Navigate to a device detail with a tab → shows device id › tab name

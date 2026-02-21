# Task 7: Sidebar Rewrite — Flat Layout with Section Labels

## Objective

Rewrite the customer sidebar from 6 collapsible groups (24+ items) to a flat layout with 3 section labels and ~16 items. Remove all `Collapsible` wrappers for the customer view. Keep the operator sidebar unchanged.

## File to Modify

`frontend/src/components/layout/AppSidebar.tsx`

---

## Current State

The customer sidebar has 6 collapsible groups: Overview, Fleet, Monitoring, Notifications, Analytics, Settings — each wrapped in `<Collapsible>` with `useState` + `localStorage` for open/close state. Total: 24+ nav items.

## Target State

The customer sidebar becomes flat with 3 section labels (non-collapsible):

```
Home
── MONITORING ──
  Dashboard
  Alerts
  Analytics
── FLEET ──
  Getting Started  (conditional)
  Devices
  Sites
  Templates
  Fleet Map
  Device Groups
  Updates
── SETTINGS ──
  Notifications
  Team             (if users.read permission)
  Billing
  Integrations
```

## Changes

### 1. Remove unused collapsible state variables

Delete all of these `useState` calls and their `onToggle` calls:
- `monitoringOpen` / `setMonitoringOpen`
- `notificationsOpen` / `setNotificationsOpen`
- `analyticsOpen` / `setAnalyticsOpen`
- `settingsOpen` / `setSettingsOpen`
- `fleetOpen` / `setFleetOpen`

Keep only:
- `fleetSetupDismissed` (for Getting Started conditional)
- Operator collapsible states (`operatorOverviewOpen`, `operatorTenantsOpen`, etc.) — these stay as-is

### 2. Remove unused nav arrays

Delete these arrays (their items are now consolidated into hub pages):
- `customerMonitoringNav` (Alerts, Alert Rules, Escalation, On-Call, Maintenance → Alerts hub)
- `customerNotificationsNav` (Channels, Delivery Log, Dead Letter → Notifications hub)
- `customerAnalyticsNav` (Analytics, Reports → Analytics hub)
- `settingsNav` (Profile, Org, Carrier, Subscription, Billing, Team, Roles → reorganized)

### 3. Add `Home` icon to imports

Add `Home` to the lucide-react import:
```tsx
import { Home, /* existing icons */ } from "lucide-react";
```

Remove icons that are no longer used in sidebar nav items (clean up as needed).

### 4. Update `isActive` function

Add special case for Home:

```tsx
function isActive(href: string) {
  if (href === "/home") {
    return location.pathname === "/home" || location.pathname === "/" || location.pathname === "";
  }
  if (href === "/dashboard") {
    return location.pathname === "/dashboard";
  }
  if (href === "/updates") {
    return location.pathname.startsWith("/updates") || location.pathname.startsWith("/ota");
  }
  if (href === "/operator") {
    return location.pathname === "/operator";
  }
  return location.pathname.startsWith(href);
}
```

The `/updates` case ensures the sidebar highlights "Updates" when viewing OTA campaign details at `/ota/campaigns/:id`.

### 5. Replace customer sidebar content

Replace everything between `<SidebarContent>` and `</SidebarContent>` for the customer view with the flat layout below. The operator view stays unchanged.

```tsx
<SidebarContent>
  {isCustomer && (
    <>
      {/* Home — standalone, above sections */}
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu>
            {renderNavItem({ label: "Home", href: "/home", icon: Home })}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      {/* Monitoring section */}
      <SidebarGroup>
        <SidebarGroupLabel>Monitoring</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {renderNavItem({ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard })}
            {renderNavItem({ label: "Alerts", href: "/alerts", icon: Bell })}
            {renderNavItem({ label: "Analytics", href: "/analytics", icon: BarChart3 })}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      {/* Fleet section */}
      <SidebarGroup>
        <SidebarGroupLabel>Fleet</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {!fleetSetupDismissed && renderNavItem({ label: "Getting Started", href: "/fleet/getting-started", icon: Rocket })}
            {renderNavItem({ label: "Devices", href: "/devices", icon: Cpu })}
            {renderNavItem({ label: "Sites", href: "/sites", icon: Building2 })}
            {renderNavItem({ label: "Templates", href: "/templates", icon: LayoutTemplate })}
            {renderNavItem({ label: "Fleet Map", href: "/map", icon: MapPin })}
            {renderNavItem({ label: "Device Groups", href: "/device-groups", icon: Layers })}
            {renderNavItem({ label: "Updates", href: "/updates", icon: Radio })}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      {/* Settings section */}
      <SidebarGroup>
        <SidebarGroupLabel>Settings</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {renderNavItem({ label: "Notifications", href: "/notifications", icon: Webhook })}
            {canManageUsers && renderNavItem({ label: "Team", href: "/team", icon: Users })}
            {renderNavItem({ label: "Billing", href: "/billing", icon: CreditCard })}
            {renderNavItem({ label: "Integrations", href: "/settings/carrier", icon: Radio })}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </>
  )}

  {/* Operator sections — KEEP UNCHANGED */}
  {isOperator && (
    // ... all existing operator SidebarGroups with Collapsibles stay exactly as-is ...
  )}
</SidebarContent>
```

### 6. Remove unused imports

After the rewrite, clean up any imports that are no longer needed:
- Remove `Collapsible`, `CollapsibleContent`, `CollapsibleTrigger` (if only used for customer nav — check if operator nav still uses them; it does, so keep)
- Remove `ChevronDown` (check if still used by operator nav)
- Remove any lucide icons that are no longer referenced

### 7. Remove `renderGroupHeader` function

This function renders the collapsible group header with chevrons. Since customer nav no longer has collapsible groups, check if it's still needed for operator nav. If operator nav still uses it, keep it. Otherwise remove it.

### 8. Clean up the `onToggle` function

If only operator nav uses collapsible state, keep `onToggle`. But remove the `readSidebarOpen` calls for customer-specific keys (`sidebar-fleet`, `sidebar-monitoring`, `sidebar-notifications`, `sidebar-analytics`, `sidebar-settings`).

## Verification

- `npx tsc --noEmit` passes
- Customer sidebar shows flat layout: Home, then 3 labeled sections
- No collapsible groups for customer view — all items always visible
- `SidebarGroupLabel` auto-hides in icon-collapse mode (shadcn/ui default behavior)
- Operator sidebar is unchanged (still has collapsible groups)
- "Home" highlights when at `/home` or `/`
- "Updates" highlights when at `/updates` or `/ota/*`
- Getting Started shows/hides based on dismiss state
- Team shows only with `users.read` permission
- Alert badge still shows on the Alerts nav item
- Total customer sidebar items: ~16 (including conditional ones)

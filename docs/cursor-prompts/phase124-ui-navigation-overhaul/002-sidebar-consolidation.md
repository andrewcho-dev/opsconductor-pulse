# Task 002: Sidebar Navigation Consolidation

## Commit message
```
refactor(ui): consolidate sidebar nav groups and fix broken links
```

## Overview
Restructure `AppSidebar.tsx` to reorganize customer navigation into cleaner logical groups, fix two broken links ("Export" and "Notification Prefs"), and remove redundant top-level items ("Jobs", "Onboarding Wizard"). Operator nav remains unchanged.

---

## Current Problems (in `frontend/src/components/layout/AppSidebar.tsx`)

1. **Broken link: "Export"** (line 77) -- `{ label: "Export", href: "/devices", icon: ScrollText }` navigates to `/devices` which is the device list, not an export page. There is no standalone export route. Export functionality belongs inside the Reports page.

2. **Broken link: "Notification Prefs"** (line 150) -- `{ label: "Notification Prefs", href: "/alerts", icon: Bell }` navigates to the alerts list page. This is misleading. Notification preferences are handled via Notification Channels at `/notifications`.

3. **"Onboarding Wizard"** (line 60) -- Clutters the Fleet group for existing users. The wizard is available at `/devices/wizard` and can be accessed from the Devices page. Remove from top-level nav.

4. **"Jobs"** (line 65) -- Listed under Monitoring but is not a core monitoring concern. Jobs are an auxiliary feature. Remove from top-level nav; the route at `/jobs` still exists for direct navigation.

5. **"Data & Integrations" group** is an odd grouping -- it mixes analytics (Metrics, Reports) with notification infrastructure (Delivery Log, Export). Split into separate groups.

---

## New Navigation Structure

### Customer groups (6 groups total)

```typescript
// ---- Group 1: Overview (non-collapsible, same as current) ----
// Dashboard  /dashboard  LayoutDashboard

// ---- Group 2: Fleet (collapsible) ----
const customerFleetNav: NavItem[] = [
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "Sites", href: "/sites", icon: Building2 },
];

// ---- Group 3: Monitoring (collapsible) ----
const customerMonitoringNav: NavItem[] = [
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
  { label: "Escalation Policies", href: "/escalation-policies", icon: ShieldAlert },
  { label: "Maintenance Windows", href: "/maintenance-windows", icon: CalendarOff },
  { label: "On-Call", href: "/oncall", icon: Users },
];

// ---- Group 4: Notifications (collapsible, new group) ----
const customerNotificationsNav: NavItem[] = [
  { label: "Channels", href: "/notifications", icon: Webhook },
  { label: "Delivery Log", href: "/delivery-log", icon: Activity },
];

// ---- Group 5: Analytics (collapsible, new group) ----
const customerAnalyticsNav: NavItem[] = [
  { label: "Metrics", href: "/metrics", icon: Gauge },
  { label: "Reports", href: "/reports", icon: ScrollText },
];

// ---- Group 6: Settings (collapsible) ----
// Built dynamically inside the component (same as current, but with fixes):
const settingsNav: NavItem[] = [
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
  ...(canManageRoles ? [{ label: "Roles", href: "/roles", icon: Shield }] : []),
  // "Notification Prefs" REMOVED -- covered by Channels above
  // "Profile" will be added in task 004
];
```

### Operator groups (unchanged)
Keep all four operator groups (`operatorOverviewNav`, `operatorTenantNav`, `operatorUsersAuditNav`, `operatorSystemNav`) exactly as they are.

---

## Step-by-Step Implementation

### Step 1: Update nav arrays at the top of AppSidebar.tsx

Replace the existing `customerFleetNav`, `customerMonitoringNav`, and `customerDataNav` arrays with the new arrays defined above. Remove the old arrays entirely.

**Lines to remove/replace:**
- Lines 56-61: Old `customerFleetNav` -- replace with new 3-item array (no Onboarding Wizard)
- Lines 63-71: Old `customerMonitoringNav` -- replace with new 5-item array (no Jobs, no Notifications)
- Lines 73-78: Old `customerDataNav` -- DELETE entirely, replaced by two new arrays

**New arrays to add** (after the fleet/monitoring arrays):
- `customerNotificationsNav` (2 items)
- `customerAnalyticsNav` (2 items)

### Step 2: Add state for new collapsible groups

Inside the `AppSidebar` component, add state for the two new groups:

```typescript
const [notificationsOpen, setNotificationsOpen] = useState(() =>
  readSidebarOpen("sidebar-notifications", false)
);
const [analyticsOpen, setAnalyticsOpen] = useState(() =>
  readSidebarOpen("sidebar-analytics", false)
);
```

### Step 3: Remove dead entries from settingsNav

Remove the "Notification Prefs" entry from `settingsNav` (currently line 150):
```typescript
// REMOVE this line:
{ label: "Notification Prefs", href: "/alerts", icon: Bell },
```

The settings array should be:
```typescript
const settingsNav: NavItem[] = [
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
  ...(canManageRoles ? [{ label: "Roles", href: "/roles", icon: Shield }] : []),
];
```

### Step 4: Update the JSX render blocks

Replace the old "Data & Integrations" collapsible block (lines 298-316) with two new blocks:

**Notifications group:**
```tsx
{isCustomer && (
  <SidebarGroup>
    <Collapsible
      open={notificationsOpen}
      onOpenChange={(next) => onToggle(setNotificationsOpen, "sidebar-notifications", next)}
    >
      <SidebarGroupLabel asChild>
        <CollapsibleTrigger className="w-full">
          {renderGroupHeader("Notifications", notificationsOpen)}
        </CollapsibleTrigger>
      </SidebarGroupLabel>
      <CollapsibleContent>
        <SidebarGroupContent>
          <SidebarMenu>{customerNotificationsNav.map((item) => renderNavItem(item))}</SidebarMenu>
        </SidebarGroupContent>
      </CollapsibleContent>
    </Collapsible>
  </SidebarGroup>
)}
```

**Analytics group:**
```tsx
{isCustomer && (
  <SidebarGroup>
    <Collapsible
      open={analyticsOpen}
      onOpenChange={(next) => onToggle(setAnalyticsOpen, "sidebar-analytics", next)}
    >
      <SidebarGroupLabel asChild>
        <CollapsibleTrigger className="w-full">
          {renderGroupHeader("Analytics", analyticsOpen)}
        </CollapsibleTrigger>
      </SidebarGroupLabel>
      <CollapsibleContent>
        <SidebarGroupContent>
          <SidebarMenu>{customerAnalyticsNav.map((item) => renderNavItem(item))}</SidebarMenu>
        </SidebarGroupContent>
      </CollapsibleContent>
    </Collapsible>
  </SidebarGroup>
)}
```

### Step 5: Clean up unused imports

After removing "Jobs" and "Onboarding Wizard" from nav arrays, check if these icons are still used:
- `Wand2` -- was used by Onboarding Wizard. Remove from imports if no longer used.
- `ClipboardList` -- was used by Jobs. Remove from imports if no longer used.

The remaining icon imports should be:
```typescript
import {
  LayoutDashboard, Cpu, Bell, Shield, ShieldAlert,
  Webhook, Activity, Gauge, Monitor, Server,
  ScrollText, Settings, Building2, CreditCard, Users,
  Layers, LayoutGrid, CalendarOff,
  ChevronRight, ChevronDown,
} from "lucide-react";
```

### Step 6: Remove `dataOpen` / `setDataOpen` state

Delete the state that was managing the old "Data & Integrations" group:
```typescript
// REMOVE:
const [dataOpen, setDataOpen] = useState(() =>
  readSidebarOpen("sidebar-data", false)
);
```

---

## Visual Layout After Changes

```
CUSTOMER SIDEBAR:
  Overview
    Dashboard
  Fleet
    Devices
    Device Groups
    Sites
  Monitoring
    Alerts [badge]
    Alert Rules
    Escalation Policies
    Maintenance Windows
    On-Call
  Notifications
    Channels
    Delivery Log
  Analytics
    Metrics
    Reports
  Settings
    Subscription
    Team (if canManageUsers)
    Roles (if canManageRoles)

OPERATOR SIDEBAR:
  (unchanged)
```

---

## Verification

1. `cd frontend && npm run build` -- zero errors, no unused import warnings.
2. Open app as customer. Sidebar shows 6 groups: Overview, Fleet, Monitoring, Notifications, Analytics, Settings.
3. Click every sidebar link. Each one navigates to the correct page without 404.
4. Confirm "Export" link is gone. Confirm "Notification Prefs" link is gone.
5. Confirm "Onboarding Wizard" and "Jobs" are not in the sidebar.
6. Collapse/expand each group. Refresh page. Collapsed state persists (localStorage).
7. Open app as operator. Sidebar shows operator groups unchanged.
8. Verify the alert count badge still shows on the "Alerts" item in the Monitoring group.

---

## Files Modified

| Action | File |
|--------|------|
| MODIFY | `frontend/src/components/layout/AppSidebar.tsx` |

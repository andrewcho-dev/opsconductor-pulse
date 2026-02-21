# Task 4: Sidebar Cleanup, Routes, CommandPalette, Breadcrumbs

## Objective

Simplify the sidebar from ~13 items to 7, add the Rules route, and update all navigation-related components.

---

## 1. Sidebar — Remove 7 items, add Rules

### File to Modify

`frontend/src/components/layout/AppSidebar.tsx`

### Changes

**1. Add import:**

Add `Scale` (or `BookOpen` or `ShieldAlert`) to the lucide-react import for the Rules icon. `Scale` is a good choice for rules/policies:

```tsx
import { ..., Scale } from "lucide-react";
```

**2. Remove unused icon imports:**

Remove icons that are no longer used in the sidebar after removing items. Check which of these are still referenced:
- `Rocket` — was used for Getting Started → **remove** (no longer in sidebar)
- `Building2` — was used for Sites → check if used elsewhere in this file (it's not) → **remove**
- `LayoutTemplate` — was used for Templates → **remove**
- `MapPin` — was used for Fleet Map → **remove**
- `Layers` — was used for Device Groups → **remove**
- `Radio` — was used for Updates → **remove**
- `Wrench` — was used for Tools → **remove**

**3. Remove the Getting Started conditional block and state:**

Remove the `fleetSetupDismissed` state:
```tsx
// DELETE:
const [fleetSetupDismissed] = useState(() => {
  return localStorage.getItem("pulse_fleet_setup_dismissed") === "true";
});
```

And remove the `useState` import if it's no longer used elsewhere in the file. (Check: `operatorOverviewOpen` etc. still use `useState`, so keep the import.)

**4. Replace the Fleet section content:**

Current Fleet section:
```tsx
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
      {renderNavItem({ label: "Tools", href: "/fleet/tools", icon: Wrench })}
    </SidebarMenu>
  </SidebarGroupContent>
</SidebarGroup>
```

Replace with:
```tsx
{/* Fleet section */}
<SidebarGroup>
  <SidebarGroupLabel>Fleet</SidebarGroupLabel>
  <SidebarGroupContent>
    <SidebarMenu>
      {renderNavItem({ label: "Devices", href: "/devices", icon: Cpu })}
      {renderNavItem({ label: "Rules", href: "/rules", icon: Scale })}
    </SidebarMenu>
  </SidebarGroupContent>
</SidebarGroup>
```

**5. Update `isActive` function:**

Add a special case for `/rules` if needed. The default `startsWith` behavior should work since `/rules` doesn't conflict with any other route prefix. No changes needed.

---

## 2. Routes — Add `/rules`, update redirects

### File to Modify

`frontend/src/app/router.tsx`

### Changes

**1. Add import:**

```tsx
import RulesHubPage from "@/features/rules/RulesHubPage";
```

**2. Add `/rules` route** inside the `RequireCustomer` children array, near the other hub routes:

```tsx
{ path: "rules", element: <RulesHubPage /> },
```

**3. Update existing redirects:**

The following existing redirects in the router point to old Alerts hub tabs. Update them to point to the Rules hub:

```tsx
// Old:
{ path: "alert-rules", element: <Navigate to="/alerts?tab=rules" replace /> },
{ path: "escalation-policies", element: <Navigate to="/alerts?tab=escalation" replace /> },
{ path: "oncall", element: <Navigate to="/alerts?tab=oncall" replace /> },
{ path: "maintenance-windows", element: <Navigate to="/alerts?tab=maintenance" replace /> },

// New:
{ path: "alert-rules", element: <Navigate to="/rules?tab=alert-rules" replace /> },
{ path: "escalation-policies", element: <Navigate to="/rules?tab=escalation" replace /> },
{ path: "oncall", element: <Navigate to="/rules?tab=oncall" replace /> },
{ path: "maintenance-windows", element: <Navigate to="/rules?tab=maintenance" replace /> },
```

**4. Remove unused imports** (if applicable):

Check if `AlertRulesPage`, `EscalationPoliciesPage`, `OncallSchedulesPage`, `MaintenanceWindowsPage` were directly imported in the router. They should not be — they were only used inside `AlertsHubPage`. Verify and clean up if needed.

---

## 3. CommandPalette — Update page list

### File to Modify

`frontend/src/components/shared/CommandPalette.tsx`

### Changes

**1. Add import:**

Add `Scale` to the lucide-react import.

**2. Update the `pages` array:**

Add Rules hub entries:
```tsx
{ label: "Rules", href: "/rules", icon: Scale },
{ label: "Alert Rules", href: "/rules?tab=alert-rules", icon: Scale },
{ label: "Escalation Policies", href: "/rules?tab=escalation", icon: Scale },
{ label: "On-Call Schedules", href: "/rules?tab=oncall", icon: Scale },
{ label: "Maintenance Windows", href: "/rules?tab=maintenance", icon: Scale },
```

Remove or update any entries that pointed to old Alerts hub tabs. Check for entries like:
- "Alert Rules" with `href: "/alerts?tab=rules"` → update to `/rules?tab=alert-rules`
- Similar for escalation, oncall, maintenance

The existing entries for Sites, Templates, Groups, Map, Updates, Tools should remain (they're still valid pages, just not in the sidebar). CommandPalette should find them via search.

---

## 4. Breadcrumbs — Add `rules` label

### File to Modify

`frontend/src/components/layout/AppHeader.tsx`

### Changes

Add `rules` to the `labelMap` in `useBreadcrumbs()`:

```tsx
rules: "Rules",
```

The breadcrumb will show just "Rules" when on `/rules`.

---

## Verification

After all changes:

```bash
cd frontend && npx tsc --noEmit
```

- Sidebar shows exactly 7 items: Home, Dashboard, Alerts, Analytics, Devices, Rules, Settings
- "Getting Started", "Sites", "Templates", "Fleet Map", "Device Groups", "Updates", "Tools" are all gone from sidebar
- Clicking "Rules" navigates to `/rules` and shows the Rules hub with 4 tabs
- Clicking "Alerts" navigates to `/alerts` and shows just the alert inbox
- CommandPalette (Cmd+K) finds "Rules", "Alert Rules", "Escalation Policies", etc.
- CommandPalette still finds "Sites", "Templates", "Groups", "Map", etc. (still in the pages list)
- Breadcrumbs show "Rules" when on the Rules page
- Old bookmark `/alert-rules` redirects to `/rules?tab=alert-rules`
- Old bookmark `/escalation-policies` redirects to `/rules?tab=escalation`

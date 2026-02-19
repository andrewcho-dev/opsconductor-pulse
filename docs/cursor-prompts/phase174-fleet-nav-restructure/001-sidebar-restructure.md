# Task 1: Sidebar Restructure

## Objective

Replace the flat `customerFleetNav` array in AppSidebar with workflow-oriented sub-groups (Setup / Monitor / Maintain), add a conditional "Getting Started" link, and remove the Sensors nav item.

## File to Modify

`frontend/src/components/layout/AppSidebar.tsx`

## Current State

Lines 61-70 define a flat `customerFleetNav` array with 8 items rendered via `.map()` inside the Fleet collapsible (line 288):

```tsx
const customerFleetNav: NavItem[] = [
  { label: "Device Templates", href: "/templates", icon: LayoutTemplate },
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Sensors", href: "/sensors", icon: Activity },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "Fleet Map", href: "/map", icon: MapPin },
  { label: "OTA Updates", href: "/ota/campaigns", icon: Radio },
  { label: "Firmware", href: "/ota/firmware", icon: Radio },
  { label: "Sites", href: "/sites", icon: Building2 },
];
```

The Fleet collapsible (lines 276-293) simply maps this array:
```tsx
<SidebarMenu>{customerFleetNav.map((item) => renderNavItem(item))}</SidebarMenu>
```

## Steps

### Step 1: Add new imports

Add `Rocket` to the lucide-react import (line 1-32 import block). `Building2`, `LayoutTemplate`, `Cpu`, `Layers`, `MapPin`, `Radio` are already imported.

Remove `Activity` from the import since Sensors nav is being removed from the sidebar (check if Activity is used elsewhere in this file first — it IS used in `operatorSystemNav` on line 113, so keep it).

### Step 2: Add Getting Started visibility state

Add a state variable for the Getting Started link visibility. After the existing `useState` hooks (around line 130), add:

```tsx
const [fleetSetupDismissed] = useState(() => {
  return localStorage.getItem("pulse_fleet_setup_dismissed") === "true";
});
```

### Step 3: Replace customerFleetNav and the Fleet collapsible content

Delete the `customerFleetNav` array (lines 61-70).

Replace the Fleet collapsible content (the `<CollapsibleContent>` block at lines 286-290) with explicitly rendered sub-groups instead of `.map()`:

```tsx
<CollapsibleContent>
  <SidebarGroupContent>
    <SidebarMenu>
      {/* Getting Started — hidden once dismissed */}
      {!fleetSetupDismissed && (
        <SidebarMenuItem>
          <SidebarMenuButton asChild isActive={isActive("/fleet/getting-started")}>
            <Link to="/fleet/getting-started">
              <Rocket className="h-4 w-4" />
              <span>Getting Started</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      )}

      {/* Setup section */}
      <div className="px-2 pt-3 pb-1">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Setup</span>
      </div>
      {renderNavItem({ label: "Sites", href: "/sites", icon: Building2 })}
      {renderNavItem({ label: "Device Templates", href: "/templates", icon: LayoutTemplate })}
      {renderNavItem({ label: "Devices", href: "/devices", icon: Cpu })}

      {/* Monitor section */}
      <div className="px-2 pt-3 pb-1">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Monitor</span>
      </div>
      {renderNavItem({ label: "Fleet Map", href: "/map", icon: MapPin })}
      {renderNavItem({ label: "Device Groups", href: "/device-groups", icon: Layers })}

      {/* Maintain section */}
      <div className="px-2 pt-3 pb-1">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Maintain</span>
      </div>
      {renderNavItem({ label: "OTA Updates", href: "/ota/campaigns", icon: Radio })}
      {renderNavItem({ label: "Firmware", href: "/ota/firmware", icon: Radio })}
    </SidebarMenu>
  </SidebarGroupContent>
</CollapsibleContent>
```

### Step 4: Verify the isActive function

The `isActive` function (line 179) uses `location.pathname.startsWith(href)`. Confirm that `/fleet/getting-started` will match correctly — it will, since `startsWith("/fleet/getting-started")` is specific enough.

## Key Decisions

- **Sub-group labels use a lightweight `<div>` with `text-xs font-medium text-muted-foreground uppercase tracking-wider`** rather than nested collapsible sections, keeping the sidebar compact.
- **Sensors is removed from navigation entirely.** The `/sensors` route is kept in the router for direct URL access; only the sidebar link is removed.
- **Getting Started visibility** uses a simple localStorage check. The GettingStartedPage (Task 2) will set this key when dismissed.
- **`Rocket` icon** is used for the Getting Started link, consistent with the existing `OnboardingChecklist` component.

## Verification

- `npx tsc --noEmit` passes
- Sidebar renders three labelled sub-groups under Fleet
- "Getting Started" link appears at top when `pulse_fleet_setup_dismissed` is not set in localStorage
- "Sensors" link is no longer in the sidebar
- All other nav items are present and functional

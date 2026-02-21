# Task 3: Add Fleet Quick-Links to Devices Page

## Objective

Add a compact navigation row to the Devices page that provides quick access to the fleet management pages removed from the sidebar: Sites, Templates, Groups, Map, Updates, Tools.

## File to Modify

`frontend/src/features/devices/DeviceListPage.tsx`

## Design

Add a single-row strip of small icon+text links between the `PageHeader` and the health status strip. These are compact pill-style buttons that navigate to the existing pages at their existing routes.

```
Devices                                      [+ Add Device ▼]
N devices in your fleet

[📍 Sites] [📐 Templates] [🗂 Groups] [🗺 Map] [📡 Updates] [🔧 Tools]

[● 12 Online] [● 3 Stale] [● 1 Offline] | 16 total devices

[Search...] [Status ▼] [Site ▼]
...device list...
```

## Implementation

**1. Add imports:**

```tsx
import { Link } from "react-router-dom";
import {
  Building2,
  LayoutTemplate,
  Layers,
  MapPin,
  Radio,
  Wrench,
} from "lucide-react";
```

Add these to the existing lucide-react import statement. `Link` should already be imported from `react-router-dom` — check and add only if missing.

**2. Define the fleet links array** (above the component or inside it):

```tsx
const FLEET_LINKS = [
  { label: "Sites", href: "/sites", icon: Building2 },
  { label: "Templates", href: "/templates", icon: LayoutTemplate },
  { label: "Groups", href: "/device-groups", icon: Layers },
  { label: "Map", href: "/map", icon: MapPin },
  { label: "Updates", href: "/updates", icon: Radio },
  { label: "Tools", href: "/fleet/tools", icon: Wrench },
];
```

**3. Add the fleet links row** — insert immediately after the `<AddDeviceModal>` component and before the health status strip:

```tsx
<div className="flex flex-wrap gap-1.5">
  {FLEET_LINKS.map((link) => {
    const Icon = link.icon;
    return (
      <Button key={link.href} variant="outline" size="sm" asChild className="h-7 text-xs">
        <Link to={link.href}>
          <Icon className="mr-1 h-3 w-3" />
          {link.label}
        </Link>
      </Button>
    );
  })}
</div>
```

**Placement in the JSX:** The fleet links row should appear between the `<AddDeviceModal>` closing tag and the `{!isLoading && devices.length > 0 && (` health status strip block. This puts it right below the page header area, always visible regardless of device count.

## Important Notes

- The links use `Button variant="outline" size="sm"` with `asChild` wrapping `Link` — this gives them the design system's button styling while functioning as navigation links
- `h-7 text-xs` makes them compact (smaller than default `sm` buttons) to avoid taking too much vertical space
- `flex-wrap` ensures they wrap gracefully on narrow screens
- The links are always visible (not conditional on loading state or device count)
- This is a lightweight change — no new components, no new state, just a row of links

## Verification

- `npx tsc --noEmit` passes
- Devices page renders the fleet links row below the page header
- Each link navigates to the correct page (Sites, Templates, Groups, Map, Updates, Tools)
- Links are compact and visually subtle (outline variant, small text)
- Links wrap correctly on narrow viewports
- The rest of the Devices page (health strip, filters, device list, detail pane) is unchanged

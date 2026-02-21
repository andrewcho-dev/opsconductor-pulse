# Task 006 — Sidebar Navigation + Route Registration

## Files to Modify

1. `frontend/src/components/layout/AppSidebar.tsx` — add "Sensors" nav item
2. `frontend/src/app/router.tsx` (or wherever routes are defined) — add sensors route

## Sidebar Change

In `AppSidebar.tsx`, find the `customerFleetNav` array (around line 60-67):

```tsx
const customerFleetNav: NavItem[] = [
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "Fleet Map", href: "/map", icon: MapPin },
  ...
];
```

Add "Sensors" after "Devices":

```tsx
const customerFleetNav: NavItem[] = [
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Sensors", href: "/sensors", icon: Activity },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "Fleet Map", href: "/map", icon: MapPin },
  ...
];
```

Import `Activity` from `lucide-react` (should already be imported — check first).

## Route Registration

Find the router configuration file (likely `frontend/src/app/router.tsx`). Add a route for the sensor list page:

```tsx
import { SensorListPage } from "@/features/devices/SensorListPage";

// In the customer route children:
{
  path: "sensors",
  element: <SensorListPage />,
},
```

Place it near the devices routes for logical grouping.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
# Then navigate to /sensors in the browser — should render the sensor list page
```

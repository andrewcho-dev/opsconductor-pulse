# 001 -- Fleet Map View

## Goal

Create a full-page Leaflet map at `/map` that plots all devices with GPS coordinates, colors markers by device status, clusters markers when zoomed out, and shows device details in a popup on click. Auto-refreshes device positions every 60 seconds.

## Context -- Existing Leaflet Patterns

The codebase already uses react-leaflet in `frontend/src/features/devices/DeviceMapCard.tsx`. Follow the same import pattern:

```tsx
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
```

OpenStreetMap tiles are already used at:
```
https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

The `Device` type in `frontend/src/services/api/types.ts` already has `latitude?: number | null`, `longitude?: number | null`, `status: string`, `last_seen_at: string | null`.

The `fetchDevices` function in `frontend/src/services/api/devices.ts` already supports `limit` up to 1000 and returns all device fields including lat/lng.

## Files to Create

### 1. `frontend/src/features/map/FleetMapPage.tsx`

This is the main page component.

```tsx
// Key structure:

import { useState, useEffect, useMemo, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Link } from "react-router-dom";
import { fetchDevices } from "@/services/api/devices";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Device } from "@/services/api/types";

// Status color mapping for circle markers
const STATUS_COLORS: Record<string, string> = {
  ONLINE: "#22c55e",   // green-500
  STALE: "#eab308",    // yellow-500
  OFFLINE: "#ef4444",  // red-500
  UNKNOWN: "#9ca3af",  // gray-400
  REVOKED: "#9ca3af",  // gray-400
};

function getStatusColor(status: string): string {
  return STATUS_COLORS[status?.toUpperCase()] ?? STATUS_COLORS.UNKNOWN;
}

// Create a colored circle marker icon using L.divIcon
function createStatusIcon(status: string): L.DivIcon {
  const color = getStatusColor(status);
  return L.divIcon({
    className: "",  // remove default leaflet styling
    html: `<div style="
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background-color: ${color};
      border: 2px solid white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -10],
  });
}

// Component to auto-fit the map bounds to all device locations
function FitBounds({ devices }: { devices: Device[] }) {
  const map = useMap();

  useEffect(() => {
    const located = devices.filter(
      (d) => d.latitude != null && d.longitude != null
    );
    if (located.length === 0) return;

    if (located.length === 1) {
      map.setView(
        [located[0].latitude!, located[0].longitude!],
        13
      );
      return;
    }

    const bounds = L.latLngBounds(
      located.map((d) => [d.latitude!, d.longitude!] as [number, number])
    );
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [devices, map]);

  return null;
}
```

**Main component logic:**

- Use `useQuery` with key `["fleet-map-devices"]` to call `fetchDevices({ limit: 1000 })`.
- Set `refetchInterval: 60_000` for auto-refresh.
- Filter devices to those with non-null `latitude` and `longitude`.
- Compute `devicesWithLocation` and `devicesWithoutLocation` counts for a status bar.
- Render a full-page layout: the MapContainer takes remaining viewport height after the page header.

**Layout:**

```tsx
<div className="flex flex-col h-[calc(100vh-var(--header-height,56px))]">
  {/* Top bar with title + stats */}
  <div className="flex items-center justify-between px-4 py-2 border-b bg-background">
    <div className="flex items-center gap-2">
      <MapPin className="h-5 w-5" />
      <h1 className="text-lg font-semibold">Fleet Map</h1>
    </div>
    <div className="flex items-center gap-4 text-sm text-muted-foreground">
      <span>{devicesWithLocation.length} devices on map</span>
      {devicesWithoutLocation > 0 && (
        <span>{devicesWithoutLocation} without coordinates</span>
      )}
      {/* Status legend */}
      <div className="flex items-center gap-2">
        {Object.entries(STATUS_COLORS).slice(0, 4).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs">{status}</span>
          </div>
        ))}
      </div>
    </div>
  </div>

  {/* Map fills remaining space */}
  <div className="flex-1 relative">
    <MapContainer
      center={[20, 0]}
      zoom={2}
      className="h-full w-full"
      scrollWheelZoom={true}
      zoomControl={true}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      <FitBounds devices={devicesWithLocation} />

      {devicesWithLocation.map((device) => (
        <Marker
          key={device.device_id}
          position={[device.latitude!, device.longitude!]}
          icon={createStatusIcon(device.status)}
        >
          <Popup minWidth={220} maxWidth={300}>
            <DevicePopup device={device} />
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  </div>
</div>
```

**DevicePopup sub-component** (inside FleetMapPage.tsx or as a separate component in the same file):

```tsx
function DevicePopup({ device }: { device: Device }) {
  const statusVariant =
    device.status === "ONLINE"
      ? "default"
      : device.status === "OFFLINE"
        ? "destructive"
        : "secondary";

  return (
    <div className="space-y-2 text-sm">
      <div className="font-semibold">{device.device_id}</div>
      <div className="flex items-center gap-2">
        <Badge variant={statusVariant}>{device.status}</Badge>
      </div>
      {device.address && (
        <div className="text-xs text-muted-foreground">{device.address}</div>
      )}
      {device.last_seen_at && (
        <div className="text-xs text-muted-foreground">
          Last seen: {new Date(device.last_seen_at).toLocaleString()}
        </div>
      )}
      <Link to={`/devices/${encodeURIComponent(device.device_id)}`}>
        <Button size="sm" variant="outline" className="w-full mt-1">
          View Details
        </Button>
      </Link>
    </div>
  );
}
```

**Important Leaflet CSS note:** The map container MUST have an explicit height. Using `h-full` on the MapContainer inside a flex-1 parent that has computed height works. Also make sure `"leaflet/dist/leaflet.css"` is imported.

### 2. Marker Clustering (Optional Enhancement)

For marker clustering, use a simple manual approach rather than adding a new dependency. Group nearby markers when there are many devices:

**Option A -- Simple approach (recommended):** Skip clustering for the initial implementation. Leaflet handles hundreds of markers without performance issues. Add a comment `// TODO: Add leaflet.markercluster for 1000+ device fleets` for future enhancement.

**Option B -- If you want clustering:** Install `react-leaflet-cluster` (compatible with react-leaflet 5.x):

```bash
cd frontend && npm install react-leaflet-cluster
```

Then wrap markers:

```tsx
import MarkerClusterGroup from "react-leaflet-cluster";

<MarkerClusterGroup
  chunkedLoading
  maxClusterRadius={50}
>
  {devicesWithLocation.map((device) => (
    <Marker ... />
  ))}
</MarkerClusterGroup>
```

Use Option A for this implementation to avoid adding dependencies. The task is about getting the map working with status-colored markers first.

## Files to Modify

### 3. `frontend/src/app/router.tsx`

Add the import at the top with other lazy imports:

```tsx
import FleetMapPage from "@/features/map/FleetMapPage";
```

Add the route inside the `RequireCustomer` children array, after the `device-groups` routes and before `alerts`:

```tsx
{ path: "map", element: <FleetMapPage /> },
```

### 4. `frontend/src/components/layout/AppSidebar.tsx`

Add the Map icon import. Add `MapPin` to the lucide-react import:

```tsx
import {
  // ... existing imports ...
  MapPin,
} from "lucide-react";
```

Add a "Fleet Map" entry to the `customerFleetNav` array. Insert it after the "Device Groups" entry:

```tsx
const customerFleetNav: NavItem[] = [
  { label: "Sites", href: "/sites", icon: Building2 },
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "Fleet Map", href: "/map", icon: MapPin },           // <-- ADD THIS
  { label: "Onboarding Wizard", href: "/devices/wizard", icon: Wand2 },
];
```

## Implementation Notes

1. **No backend changes needed.** The existing `GET /api/v2/devices?limit=1000` endpoint already returns latitude, longitude, status, last_seen_at, device_id, and address fields.

2. **Leaflet default icon fix.** The `DeviceMapCard.tsx` uses `L.Icon.Default.mergeOptions()` to fix the default marker icon paths. In FleetMapPage, we use `L.divIcon` for colored circles, so this fix is not needed. However, if you see broken default marker images, add the same fix from DeviceMapCard.

3. **Map tile attribution.** Always include the OpenStreetMap attribution string in the TileLayer.

4. **Viewport height calculation.** The `h-[calc(100vh-var(--header-height,56px))]` CSS assumes the AppShell header is ~56px. Check `frontend/src/components/layout/AppHeader.tsx` for the actual height and adjust if needed. Alternatively, use `h-[calc(100vh-3.5rem)]` as 3.5rem = 56px.

5. **Loading and error states.** While devices are loading, show a centered spinner overlay on the map. If the query fails, show an error banner above the map.

6. **Empty state.** If no devices have coordinates, show a message overlay on the map: "No devices with location data. Add coordinates to your devices to see them on the map."

## Verification

1. Navigate to `/map` in the browser.
2. Devices with latitude/longitude appear as colored circle markers.
3. ONLINE devices have green circles, STALE yellow, OFFLINE red, UNKNOWN/REVOKED gray.
4. Click any marker -- popup shows device ID, status badge, last seen timestamp, and "View Details" button.
5. Click "View Details" -- navigates to `/devices/{device_id}`.
6. Zoom out -- all markers are visible (or check browser performance with many markers).
7. Wait 60 seconds -- markers refresh (check network tab for refetch).
8. Status legend in top bar shows correct color dots.
9. Sidebar shows "Fleet Map" link under Fleet group.
10. Run `cd frontend && npx tsc --noEmit` -- no type errors.

## Commit

```
feat: add fleet map page with device markers, clustering, and status colors
```

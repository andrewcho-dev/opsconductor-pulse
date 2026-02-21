# 138-003: Add Map Marker Clustering

## Task
Address the TODO at `features/map/FleetMapPage.tsx:13` by adding marker clustering for large device fleets.

## File
`frontend/src/features/map/FleetMapPage.tsx`

## Current State
- Uses React Leaflet (TileLayer, Marker, Popup, MapContainer)
- Custom SVG-based div icons with color coding (green=ONLINE, yellow=STALE, red=OFFLINE, gray=UNKNOWN)
- Fetches up to 1000 devices with 60-second refetch
- TODO comment: `// TODO: Add leaflet.markercluster for 1000+ device fleets.`

## Steps

### 1. Install Dependencies
```bash
cd frontend
npm install react-leaflet-cluster
```

**Note**: `react-leaflet-cluster` is the maintained React wrapper for Leaflet.markercluster. If it's not compatible with the current react-leaflet version, try `@changey/react-leaflet-markercluster` or install the raw `leaflet.markercluster` and create a simple wrapper.

Also ensure the markercluster CSS is imported:
```bash
npm install leaflet.markercluster
```

### 2. Add CSS Import
In the FleetMapPage or a global CSS file:
```typescript
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
```

### 3. Wrap Markers in MarkerClusterGroup

```typescript
import MarkerClusterGroup from "react-leaflet-cluster";

// Custom cluster icon based on worst device status in cluster
function createClusterIcon(cluster: any) {
  const markers = cluster.getAllChildMarkers();
  const statuses = markers.map((m: any) => m.options.data?.status);

  let color = "#22c55e"; // green (all online)
  if (statuses.includes("OFFLINE") || statuses.includes("DECOMMISSIONED")) {
    color = "#ef4444"; // red
  } else if (statuses.includes("STALE")) {
    color = "#eab308"; // yellow
  }

  return L.divIcon({
    html: `<div style="
      background-color: ${color};
      color: white;
      border-radius: 50%;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: bold;
      border: 2px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    ">${cluster.getChildCount()}</div>`,
    className: "custom-cluster-icon",
    iconSize: L.point(36, 36),
  });
}
```

### 4. Update the Map JSX

Replace the bare marker mapping with a clustered group:

```typescript
<MapContainer center={center} zoom={zoom} ...>
  <TileLayer url="..." attribution="..." />

  <MarkerClusterGroup
    chunkedLoading
    iconCreateFunction={createClusterIcon}
    maxClusterRadius={50}
    spiderfyOnMaxZoom
    showCoverageOnHover={false}
    zoomToBoundsOnClick
  >
    {locatedDevices.map((device) => (
      <Marker
        key={device.device_id}
        position={[device.latitude!, device.longitude!]}
        icon={getDeviceIcon(device.status)}
        data={device}  // Pass device data for cluster icon coloring
      >
        <Popup>
          {/* existing popup content */}
        </Popup>
      </Marker>
    ))}
  </MarkerClusterGroup>
</MapContainer>
```

### 5. Pass Device Data to Markers
The custom cluster icon needs access to each marker's device status. Pass it via the marker's options:

```typescript
// When creating markers, ensure the device data is accessible
// This may require extending the Marker props or using eventHandlers
```

If `react-leaflet-cluster` doesn't support custom data on markers, use an alternative approach:
- Store device data in a Map keyed by lat/lng
- In `iconCreateFunction`, look up statuses from the data map

### 6. Remove the TODO Comment
Delete line 13: `// TODO: Add leaflet.markercluster for 1000+ device fleets.`

### 7. Add Custom CSS
Add to prevent default Leaflet cluster styles from conflicting:
```css
.custom-cluster-icon {
  background: transparent !important;
  border: none !important;
}
```

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```

Manual:
- With 50+ devices with locations: zoom out → see cluster circles with count
- Cluster color: red if any device is OFFLINE, yellow if any STALE, green if all ONLINE
- Click cluster → zoom in to reveal individual markers
- At max zoom with overlapping markers → spiderfy (spread out)
- Individual markers still show popup with device info on click
- Performance: map with 1000+ markers should render smoothly

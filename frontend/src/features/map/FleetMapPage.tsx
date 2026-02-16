import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import { MapPin, Loader2 } from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Link } from "react-router-dom";
import { fetchDevices } from "@/services/api/devices";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Device } from "@/services/api/types";

// TODO: Add leaflet.markercluster for 1000+ device fleets.

const STATUS_COLORS: Record<string, string> = {
  ONLINE: "#22c55e", // green-500
  STALE: "#eab308", // yellow-500
  OFFLINE: "#ef4444", // red-500
  UNKNOWN: "#9ca3af", // gray-400
  REVOKED: "#9ca3af", // gray-400
};

function getStatusColor(status: string): string {
  return STATUS_COLORS[status?.toUpperCase()] ?? STATUS_COLORS.UNKNOWN;
}

function createStatusIcon(status: string): L.DivIcon {
  const color = getStatusColor(status);
  return L.divIcon({
    className: "",
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

function FitBounds({ devices }: { devices: Device[] }) {
  const map = useMap();

  useEffect(() => {
    const located = devices.filter((d) => d.latitude != null && d.longitude != null);
    if (located.length === 0) return;

    if (located.length === 1) {
      map.setView([located[0].latitude!, located[0].longitude!], 13);
      return;
    }

    const bounds = L.latLngBounds(
      located.map((d) => [d.latitude!, d.longitude!] as [number, number])
    );
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [devices, map]);

  return null;
}

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

export default function FleetMapPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fleet-map-devices"],
    queryFn: () => fetchDevices({ limit: 1000, offset: 0 }),
    refetchInterval: 60_000,
  });

  const devices = data?.devices ?? [];

  const devicesWithLocation = useMemo(
    () => devices.filter((d) => d.latitude != null && d.longitude != null),
    [devices]
  );
  const devicesWithoutLocation = devices.length - devicesWithLocation.length;

  return (
    <div className="-m-6 flex flex-col h-[calc(100vh-var(--header-height,56px))]">
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
          <div className="flex items-center gap-2">
            {Object.entries(STATUS_COLORS)
              .slice(0, 4)
              .map(([status, color]) => (
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

      {isError && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive border-b">
          Failed to load devices for map.
        </div>
      )}

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

        {isLoading && (
          <div className="absolute inset-0 bg-background/40 flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading devices...
            </div>
          </div>
        )}

        {!isLoading && devicesWithLocation.length === 0 && !isError && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="rounded-md border border-border bg-background/90 px-4 py-3 text-sm text-muted-foreground">
              No devices with location data. Add coordinates to your devices to see them
              on the map.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


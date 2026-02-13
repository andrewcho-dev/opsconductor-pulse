import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { useMemo, useRef } from "react";
import L from "leaflet";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import "leaflet/dist/leaflet.css";

L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

interface DeviceMapCardProps {
  latitude?: number | null;
  longitude?: number | null;
  address?: string | null;
  editable?: boolean;
  onLocationChange?: (lat: number, lng: number) => void;
}

function DraggableMarker({
  position,
  onDragEnd,
}: {
  position: [number, number];
  onDragEnd: (lat: number, lng: number) => void;
}) {
  const markerRef = useRef<L.Marker>(null);

  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (marker) {
          const { lat, lng } = marker.getLatLng();
          onDragEnd(lat, lng);
        }
      },
    }),
    [onDragEnd]
  );

  return (
    <Marker
      draggable
      eventHandlers={eventHandlers}
      position={position}
      ref={markerRef}
    >
      <Popup>Drag to adjust location</Popup>
    </Marker>
  );
}

export function DeviceMapCard({
  latitude,
  longitude,
  address,
  editable = false,
  onLocationChange,
}: DeviceMapCardProps) {
  const hasLocation = latitude != null && longitude != null;

  if (!hasLocation && !address) {
    return (
      <div className="border rounded p-2 bg-card h-full flex items-center justify-center text-xs text-muted-foreground">
        No location set
      </div>
    );
  }

  if (!hasLocation) {
    return (
      <div className="border rounded p-2 bg-card h-full flex items-center justify-center text-xs text-muted-foreground">
        Address: {address} (no coordinates)
      </div>
    );
  }

  const handleDragEnd = (lat: number, lng: number) => {
    if (onLocationChange) {
      onLocationChange(lat, lng);
    }
  };

  return (
    <div className="border rounded overflow-hidden h-full relative min-h-[160px]">
      {editable && (
        <div className="absolute top-1 left-1 z-[1000] bg-background/90 text-[10px] px-1 py-0.5 rounded">
          Drag marker to adjust
        </div>
      )}
      <MapContainer
        center={[latitude as number, longitude as number]}
        zoom={15}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={editable}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap"
        />
        {editable ? (
          <DraggableMarker
            position={[latitude as number, longitude as number]}
            onDragEnd={handleDragEnd}
          />
        ) : (
          <Marker position={[latitude as number, longitude as number]}>
            <Popup>{address || `${latitude}, ${longitude}`}</Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}

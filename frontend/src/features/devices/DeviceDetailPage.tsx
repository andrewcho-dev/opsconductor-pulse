import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useDevice } from "@/hooks/use-devices";
import { useDeviceTelemetry } from "@/hooks/use-device-telemetry";
import { useDeviceAlerts } from "@/hooks/use-device-alerts";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { DeviceInfoCard } from "./DeviceInfoCard";
import { DeviceMapCard } from "./DeviceMapCard";
import { DeviceEditModal } from "./DeviceEditModal";
import { TelemetryChartsSection } from "./TelemetryChartsSection";
import { ArrowLeft } from "lucide-react";
import {
  getDeviceTags,
  setDeviceTags,
  updateDevice,
} from "@/services/api/devices";
import { getLatestValue } from "@/lib/charts/transforms";

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const queryClient = useQueryClient();

  // Device info from REST
  const { data: deviceData, isLoading: deviceLoading } = useDevice(deviceId || "");

  // Telemetry data (REST + WS fused)
  const {
    points,
    metrics,
    isLoading: telemetryLoading,
    isLive,
    liveCount,
    timeRange,
    setTimeRange,
  } = useDeviceTelemetry(deviceId || "");
  const { data: alertsData } = useDeviceAlerts(deviceId || "", "OPEN", 50);

  const device = deviceData?.device;

  const [notesValue, setNotesValue] = useState("");
  const [notesSaving, setNotesSaving] = useState(false);
  const [tagsSaving, setTagsSaving] = useState(false);
  const [deviceTags, setDeviceTagsState] = useState<string[]>([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [pendingLocation, setPendingLocation] = useState<{ lat: number; lng: number } | null>(
    null
  );

  useEffect(() => {
    if (!device) return;
    setNotesValue(device.notes ?? "");
  }, [device]);

  useEffect(() => {
    const currentDeviceId = deviceId;
    if (!currentDeviceId) return;
    const deviceIdValue = currentDeviceId as string;
    let isMounted = true;
    async function loadTags() {
      try {
        const response = await getDeviceTags(deviceIdValue);
        if (isMounted) {
          setDeviceTagsState(response.tags);
        }
      } catch (error) {
        console.error("Failed to load device tags:", error);
        if (isMounted) {
          setDeviceTagsState([]);
        }
      }
    }
    loadTags();
    return () => {
      isMounted = false;
    };
  }, [deviceId]);

  const openAlertCount = alertsData?.alerts?.length ?? 0;

  async function refreshDevice() {
    if (!deviceId) return;
    await queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
  }

  async function handleSaveNotes() {
    if (!deviceId) return;
    setNotesSaving(true);
    try {
      await updateDevice(deviceId, { notes: notesValue || null });
      await refreshDevice();
    } finally {
      setNotesSaving(false);
    }
  }

  function handleNotesChange(value: string) {
    setNotesValue(value);
  }

  function formatMetricValue(metricName: string) {
    const value = getLatestValue(points, metricName);
    if (value == null || Number.isNaN(value)) return "—";
    return String(value);
  }

  async function handleSaveTags(tags: string[]) {
    if (!deviceId) return;
    setTagsSaving(true);
    try {
      await setDeviceTags(deviceId, tags);
    } finally {
      setTagsSaving(false);
    }
  }

  async function handleSaveDevice(update: Parameters<typeof updateDevice>[1]) {
    if (!deviceId) return;
    await updateDevice(deviceId, update);
    await refreshDevice();
    if (update.notes != null) {
      setNotesValue(update.notes ?? "");
    }
  }

  const handleMapLocationChange = (lat: number, lng: number) => {
    setPendingLocation({ lat, lng });
  };

  const handleSaveLocation = async () => {
    if (!pendingLocation || !deviceId) return;
    await updateDevice(deviceId, {
      latitude: pendingLocation.lat,
      longitude: pendingLocation.lng,
      location_source: "manual",
    });
    await refreshDevice();
    setPendingLocation(null);
  };

  return (
    <div className="p-3 space-y-3">
      <Link
        to="/devices"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Devices
      </Link>

      <div className="grid grid-cols-2 gap-2">
        <DeviceInfoCard
          device={device}
          isLoading={deviceLoading}
          tags={deviceTags}
          onTagsChange={(next) => {
            setDeviceTagsState(next);
            void handleSaveTags(next);
          }}
          notesValue={notesValue}
          onNotesChange={handleNotesChange}
          onNotesBlur={handleSaveNotes}
          onEdit={() => setEditModalOpen(true)}
        />
        <div className="relative">
          <DeviceMapCard
            latitude={pendingLocation?.lat ?? device?.latitude}
            longitude={pendingLocation?.lng ?? device?.longitude}
            address={device?.address}
            editable
            onLocationChange={handleMapLocationChange}
          />
          {pendingLocation && (
            <div className="absolute bottom-2 right-2 z-[1000] flex gap-1">
              <Button size="sm" className="h-6 text-xs" onClick={handleSaveLocation}>
                Save Location
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-xs"
                onClick={() => setPendingLocation(null)}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {metrics.slice(0, 8).map((metricName) => (
          <div key={metricName} className="border rounded p-1 text-center">
            <div className="text-[10px] text-muted-foreground truncate">
              {metricName}
            </div>
            <div className="text-sm font-semibold">
              {formatMetricValue(metricName)}
            </div>
          </div>
        ))}
      </div>

      <WidgetErrorBoundary widgetName="Telemetry Charts">
        <div className="h-[calc(100vh-320px)]">
          <TelemetryChartsSection
            metrics={metrics}
            points={points}
            isLoading={telemetryLoading}
            isLive={isLive}
            liveCount={liveCount}
            timeRange={timeRange}
            onTimeRangeChange={setTimeRange}
          />
        </div>
      </WidgetErrorBoundary>

      {notesSaving && (
        <div className="text-[10px] text-muted-foreground">Saving notes...</div>
      )}
      {tagsSaving && (
        <div className="text-[10px] text-muted-foreground">Saving tags...</div>
      )}

      {openAlertCount > 0 && (
        <Link to="/alerts" className="text-xs text-primary hover:underline">
          View {openAlertCount} alerts
        </Link>
      )}

      {device && (
        <DeviceEditModal
          device={device}
          open={editModalOpen}
          onSave={handleSaveDevice}
          onClose={() => setEditModalOpen(false)}
        />
      )}
    </div>
  );
}

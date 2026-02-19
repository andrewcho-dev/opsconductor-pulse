import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared";
import { useDevice } from "@/hooks/use-devices";
import { useDeviceTelemetry } from "@/hooks/use-device-telemetry";
import { useDeviceAlerts } from "@/hooks/use-device-alerts";
import { DeviceInfoCard } from "./DeviceInfoCard";
import { DeviceMapCard } from "./DeviceMapCard";
import { DeviceEditModal } from "./DeviceEditModal";
import { DevicePlanPanel } from "./DevicePlanPanel";
import { CreateJobModal } from "@/features/jobs/CreateJobModal";
import {
  getDeviceTags,
  setDeviceTags,
  updateDevice,
} from "@/services/api/devices";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import { DeviceSensorsDataTab } from "./DeviceSensorsDataTab";
import { DeviceTransportTab } from "./DeviceTransportTab";
import { DeviceHealthTab } from "./DeviceHealthTab";
import { DeviceTwinCommandsTab } from "./DeviceTwinCommandsTab";
import { DeviceSecurityTab } from "./DeviceSecurityTab";

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
  const [createJobOpen, setCreateJobOpen] = useState(false);

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
        toast.error(getErrorMessage(error) || "Failed to load device tags");
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
    <div className="space-y-4">
      <PageHeader
        title={device?.device_id ?? "Device"}
        description={device?.model || undefined}
        breadcrumbs={[
          { label: "Devices", href: "/devices" },
          { label: device?.device_id ?? "..." },
        ]}
        action={
          <div className="flex items-center gap-2">
            {device?.template ? (
              <Badge variant="outline">
                <Link to={`/templates/${device.template.id}`}>{device.template.name}</Link>
              </Badge>
            ) : null}
            <Button size="sm" variant="outline" onClick={() => setEditModalOpen(true)}>
              Edit
            </Button>
            <Button size="sm" variant="outline" onClick={() => setCreateJobOpen(true)}>
              Create Job
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sensors">Sensors & Data</TabsTrigger>
          <TabsTrigger value="transport">Transport</TabsTrigger>
          <TabsTrigger value="health">Health</TabsTrigger>
          <TabsTrigger value="twin">Twin & Commands</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="pt-2 space-y-4">
          <div className="grid grid-cols-2 gap-4">
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
                  <Button size="sm" className="h-8" onClick={handleSaveLocation}>
                    Save Location
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8"
                    onClick={() => setPendingLocation(null)}
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          </div>

          {deviceId && <DevicePlanPanel deviceId={deviceId} />}

          {notesSaving && <div className="text-sm text-muted-foreground">Saving notes...</div>}
          {tagsSaving && <div className="text-sm text-muted-foreground">Saving tags...</div>}
          {openAlertCount > 0 && (
            <Link to="/alerts" className="text-sm text-primary hover:underline">
              View {openAlertCount} alerts
            </Link>
          )}
        </TabsContent>

        <TabsContent value="sensors">
          {deviceId ? (
            <DeviceSensorsDataTab
              deviceId={deviceId}
              templateId={device?.template_id ?? null}
              telemetry={{
                points,
                metrics,
                isLoading: telemetryLoading,
                isLive,
                liveCount,
                timeRange,
                onTimeRangeChange: setTimeRange,
              }}
            />
          ) : null}
        </TabsContent>

        <TabsContent value="transport">
          {deviceId ? <DeviceTransportTab deviceId={deviceId} /> : null}
        </TabsContent>

        <TabsContent value="health">
          {deviceId ? <DeviceHealthTab deviceId={deviceId} /> : null}
        </TabsContent>

        <TabsContent value="twin">
          {deviceId ? (
            <DeviceTwinCommandsTab deviceId={deviceId} templateId={device?.template_id ?? null} />
          ) : null}
        </TabsContent>

        <TabsContent value="security">
          {deviceId ? <DeviceSecurityTab deviceId={deviceId} /> : null}
        </TabsContent>
      </Tabs>

      {device && (
        <DeviceEditModal
          device={device}
          open={editModalOpen}
          onSave={handleSaveDevice}
          onClose={() => setEditModalOpen(false)}
        />
      )}
      {createJobOpen && device && (
        <CreateJobModal
          prefilledDeviceId={device.device_id}
          onClose={() => setCreateJobOpen(false)}
          onCreated={() => setCreateJobOpen(false)}
        />
      )}
    </div>
  );
}

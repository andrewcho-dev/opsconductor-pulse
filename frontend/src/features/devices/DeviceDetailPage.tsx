import { useEffect, useMemo, useState } from "react";
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

function relativeTime(input?: string | null) {
  if (!input) return "never";
  const deltaMs = Date.now() - new Date(input).getTime();
  if (!Number.isFinite(deltaMs) || deltaMs < 0) return "just now";
  const minutes = Math.floor(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function statusDot(status?: string) {
  if (status === "ONLINE") return "bg-status-online";
  if (status === "STALE") return "bg-status-stale";
  return "bg-status-offline";
}

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
  const latestMetrics = useMemo(() => {
    const latest = points.at(-1);
    if (!latest) return [];
    return Object.entries(latest.metrics).slice(0, 12);
  }, [points]);

  async function refreshDevice() {
    if (!deviceId) return;
    await queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
  }

  async function handleSaveNotes() {
    if (!deviceId) return;
    try {
      await updateDevice(deviceId, { notes: notesValue || null });
      await refreshDevice();
    } catch (error) {
      toast.error(getErrorMessage(error) || "Failed to save notes");
    }
  }

  function handleNotesChange(value: string) {
    setNotesValue(value);
  }

  async function handleSaveTags(tags: string[]) {
    if (!deviceId) return;
    try {
      await setDeviceTags(deviceId, tags);
    } catch (error) {
      toast.error(getErrorMessage(error) || "Failed to save tags");
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
        description={
          device
            ? [device.model, device.manufacturer, device.site_id ? `Site: ${device.site_id}` : null]
                .filter(Boolean)
                .join(" · ") || undefined
            : undefined
        }
        breadcrumbs={[
          { label: "Devices", href: "/devices" },
          { label: device?.device_id ?? "..." },
        ]}
        action={
          <div className="flex items-center gap-2">
            {device ? (
              <Badge
                variant="outline"
                className={
                  device.status === "ONLINE"
                    ? "border-green-500 text-green-600"
                    : device.status === "STALE"
                      ? "border-yellow-500 text-yellow-600"
                      : "border-red-500 text-red-600"
                }
              >
                <span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${statusDot(device.status)}`} />
                {device.status} · {relativeTime(device.last_seen_at)}
              </Badge>
            ) : null}
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

      {/* KPI strip — above tabs */}
      <div className="grid grid-cols-5 gap-3">
        <div className="rounded-md border border-border p-3">
          <div className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-full ${statusDot(device?.status)}`} />
            <span className="text-sm font-semibold">{device?.status ?? "—"}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">{relativeTime(device?.last_seen_at)}</div>
        </div>
        <div className="rounded-md border border-border p-3">
          <div className="text-lg font-semibold">{device?.sensor_count ?? "—"}</div>
          <div className="text-xs text-muted-foreground">Sensors</div>
        </div>
        <div className="rounded-md border border-border p-3">
          <div className={`text-lg font-semibold ${openAlertCount > 0 ? "text-destructive" : ""}`}>
            {openAlertCount}
          </div>
          <div className="text-xs text-muted-foreground">Open Alerts</div>
        </div>
        <div className="rounded-md border border-border p-3">
          <div className="text-lg font-semibold">{device?.fw_version ?? "—"}</div>
          <div className="text-xs text-muted-foreground">Firmware</div>
        </div>
        <div className="rounded-md border border-border p-3">
          <div className="text-lg font-semibold">{device?.plan_id ?? "—"}</div>
          <div className="text-xs text-muted-foreground">Plan</div>
        </div>
      </div>

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
          <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
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

            <div className="space-y-4">
              <div className="rounded-md border border-border p-4">
                <h4 className="mb-3 text-sm font-semibold">Latest Telemetry</h4>
                {latestMetrics.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No telemetry data yet.</p>
                ) : (
                  <div className="space-y-2">
                    {latestMetrics.map(([name, value]) => (
                      <div key={name} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{name}</span>
                        <span className="font-mono font-medium">{String(value)}</span>
                      </div>
                    ))}
                    <div className="pt-1 text-right text-xs text-muted-foreground">
                      Updated {relativeTime(points.at(-1)?.timestamp)}
                    </div>
                  </div>
                )}
              </div>

              {device?.latitude != null && device?.longitude != null && (
                <div className="relative">
                  <DeviceMapCard
                    latitude={pendingLocation?.lat ?? device.latitude}
                    longitude={pendingLocation?.lng ?? device.longitude}
                    address={device.address}
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
              )}
            </div>
          </div>

          {deviceId && (
            <section>
              <DevicePlanPanel deviceId={deviceId} />
            </section>
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

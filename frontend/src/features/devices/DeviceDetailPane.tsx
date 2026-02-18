import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDevice } from "@/hooks/use-devices";
import { useDeviceTelemetry } from "@/hooks/use-device-telemetry";
import { useDeviceAlerts } from "@/hooks/use-device-alerts";
import { decommissionDevice, getDeviceTags } from "@/services/api/devices";
import { acknowledgeAlert, closeAlert, silenceAlert } from "@/services/api/alerts";
import { DeviceApiTokensPanel } from "./DeviceApiTokensPanel";
import { DeviceUptimePanel } from "./DeviceUptimePanel";
import { DeviceTwinPanel } from "./DeviceTwinPanel";
import { TelemetryChartsSection } from "./TelemetryChartsSection";
import { EditDeviceModal } from "./EditDeviceModal";

interface DeviceDetailPaneProps {
  deviceId: string;
}

const SILENCE_OPTIONS = [
  { label: "15m", value: 15 },
  { label: "1h", value: 60 },
  { label: "4h", value: 240 },
  { label: "24h", value: 1440 },
] as const;

function statusDot(status?: string) {
  if (status === "ONLINE") return "bg-status-online";
  if (status === "STALE") return "bg-status-stale";
  return "bg-status-offline";
}

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

export function DeviceDetailPane({ deviceId }: DeviceDetailPaneProps) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("overview");
  const [editOpen, setEditOpen] = useState(false);
  const [confirmDecommission, setConfirmDecommission] = useState<string | null>(null);
  const { data: deviceData } = useDevice(deviceId);
  const { data: tagData } = useQuery({
    queryKey: ["device-tags", deviceId],
    queryFn: () => getDeviceTags(deviceId),
    enabled: !!deviceId,
  });
  const { data: alertsData } = useDeviceAlerts(deviceId, "OPEN", 50);
  const {
    points,
    metrics,
    isLoading: telemetryLoading,
    isLive,
    liveCount,
    timeRange,
    setTimeRange,
  } = useDeviceTelemetry(deviceId);

  const device = deviceData?.device;
  const tags = tagData?.tags ?? [];
  const activeAlertCount = alertsData?.alerts?.length ?? 0;
  const latestMetrics = useMemo(() => {
    const latest = points.at(-1);
    if (!latest) return [];
    return Object.entries(latest.metrics).slice(0, 8);
  }, [points]);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["device", deviceId] });
    await queryClient.invalidateQueries({ queryKey: ["device-alerts", deviceId] });
    await queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };

  if (!device) {
    return <div className="p-6 text-sm text-muted-foreground">Loading device details...</div>;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${statusDot(device.status)}`} />
              <h3 className="text-lg font-semibold">{device.device_id}</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              {(device.model || "unknown-type")} | Site: {device.site_id}
            </p>
            <div className="flex flex-wrap gap-1">
              {tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
              {tags.length === 0 && (
                <span className="text-sm text-muted-foreground">No tags</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
              Edit
            </Button>
            <details className="relative">
              <summary className="cursor-pointer rounded border border-border px-2 py-1 text-sm">
                ⋮
              </summary>
              <div className="absolute right-0 z-10 mt-1 w-40 rounded border border-border bg-background p-1 shadow-md">
                <button
                  onClick={async () => {
                    setConfirmDecommission(device.device_id);
                  }}
                  className="block w-full rounded px-2 py-1 text-left text-sm hover:bg-accent"
                >
                  Decommission
                </button>
                <Link
                  to={`/devices/${device.device_id}`}
                  className="block rounded px-2 py-1 text-left text-sm hover:bg-accent"
                >
                  View Full Page
                </Link>
              </div>
            </details>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="telemetry">Telemetry</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="twin">Twin</TabsTrigger>
            <TabsTrigger value="tokens">Tokens</TabsTrigger>
            <TabsTrigger value="uptime">Uptime</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 pt-2">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded border border-border p-3">
                <div className="text-sm text-muted-foreground">Last Seen</div>
                <div className="text-sm font-medium">{relativeTime(device.last_seen_at)}</div>
              </div>
              <div className="rounded border border-border p-3">
                <div className="text-sm text-muted-foreground">Provision Date</div>
                <div className="text-sm font-medium">{device.last_heartbeat_at || "—"}</div>
              </div>
              <div className="rounded border border-border p-3">
                <div className="text-sm text-muted-foreground">Device ID</div>
                <div className="flex items-center justify-between gap-2">
                  <code className="text-sm">{device.device_id}</code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigator.clipboard.writeText(device.device_id)}
                  >
                    Copy
                  </Button>
                </div>
              </div>
            </div>

            <div className="rounded border border-border p-3">
              <div className="mb-2 flex items-center justify-between">
                <h4 className="text-sm font-semibold">Current Telemetry Snapshot</h4>
                <Button size="sm" variant="outline" onClick={() => setTab("alerts")}>
                  Active Alerts: {activeAlertCount}
                </Button>
              </div>
              {latestMetrics.length === 0 ? (
                <p className="text-sm text-muted-foreground">No telemetry yet.</p>
              ) : (
                <div className="grid gap-2 md:grid-cols-4">
                  {latestMetrics.map(([name, value]) => (
                    <div key={name} className="rounded border border-border p-2">
                      <div className="text-sm text-muted-foreground">{name}</div>
                      <div className="text-sm font-medium">{String(value)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="telemetry" className="pt-2">
            <TelemetryChartsSection
              deviceId={deviceId}
              metrics={metrics}
              points={points}
              isLoading={telemetryLoading}
              isLive={isLive}
              liveCount={liveCount}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
            />
          </TabsContent>

          <TabsContent value="alerts" className="space-y-2 pt-2">
            {(alertsData?.alerts ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No open alerts for this device.</p>
            ) : (
              (alertsData?.alerts ?? []).map((alert) => (
                <div key={alert.alert_id} className="rounded border border-border p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <div className="text-sm font-medium">{alert.alert_type}</div>
                    <Badge variant="outline">S{alert.severity}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{alert.summary}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        await acknowledgeAlert(String(alert.alert_id));
                        await refresh();
                      }}
                    >
                      Acknowledge
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        await closeAlert(String(alert.alert_id));
                        await refresh();
                      }}
                    >
                      Close
                    </Button>
                    {SILENCE_OPTIONS.map((opt) => (
                      <Button
                        key={opt.value}
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          await silenceAlert(String(alert.alert_id), opt.value);
                          await refresh();
                        }}
                      >
                        Silence {opt.label}
                      </Button>
                    ))}
                  </div>
                </div>
              ))
            )}
          </TabsContent>

          <TabsContent value="twin" className="pt-2">
            <DeviceTwinPanel deviceId={deviceId} />
          </TabsContent>

          <TabsContent value="tokens" className="pt-2">
            <DeviceApiTokensPanel deviceId={deviceId} />
          </TabsContent>

          <TabsContent value="uptime" className="pt-2">
            <DeviceUptimePanel deviceId={deviceId} />
          </TabsContent>
        </Tabs>
      </div>

      <EditDeviceModal
        open={editOpen}
        device={device}
        onClose={() => setEditOpen(false)}
        onSaved={refresh}
      />

      <AlertDialog open={!!confirmDecommission} onOpenChange={(open) => !open && setConfirmDecommission(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Decommission Device</AlertDialogTitle>
            <AlertDialogDescription>
              Decommission {confirmDecommission}? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (!confirmDecommission) return;
                await decommissionDevice(confirmDecommission);
                await refresh();
                setConfirmDecommission(null);
              }}
            >
              Decommission
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  createDeviceTransport,
  deleteDeviceTransport,
  listDeviceTransports,
  updateDeviceTransport,
} from "@/services/api/devices";
import { listCarrierIntegrations } from "@/services/api/carrier";
import type { DeviceTransport, TransportCreatePayload, TransportUpdatePayload } from "@/services/api/types";
import { getErrorMessage } from "@/lib/errors";

const protocolLabels: Record<string, string> = {
  mqtt_direct: "MQTT Direct",
  http_api: "HTTP API",
  lorawan: "LoRaWAN",
  gateway_proxy: "Gateway Proxy",
  modbus_rtu: "Modbus RTU",
};

const connectivityLabels: Record<string, string> = {
  cellular: "Cellular",
  ethernet: "Ethernet",
  wifi: "WiFi",
  satellite: "Satellite",
  lora: "LoRa",
  other: "Other",
};

function parseJsonObject(input: string): Record<string, unknown> {
  const trimmed = input.trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Config must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}

function pretty(obj: unknown) {
  try {
    return JSON.stringify(obj ?? {}, null, 2);
  } catch {
    return "{}";
  }
}

type TransportDialogMode = "create" | "edit";

function TransportDialog({
  deviceId,
  mode,
  initial,
  onDone,
}: {
  deviceId: string;
  mode: TransportDialogMode;
  initial?: DeviceTransport;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [ingestionProtocol, setIngestionProtocol] = useState<string>(initial?.ingestion_protocol ?? "mqtt_direct");
  const [physicalConnectivity, setPhysicalConnectivity] = useState<string>(initial?.physical_connectivity ?? "");
  const [carrierIntegrationId, setCarrierIntegrationId] = useState<string>(
    initial?.carrier_integration?.id != null ? String(initial.carrier_integration.id) : ""
  );
  const [isPrimary, setIsPrimary] = useState<boolean>(initial?.is_primary ?? false);
  const [status, setStatus] = useState<string>(initial?.status ?? "active");
  const [protocolConfigText, setProtocolConfigText] = useState<string>(pretty(initial?.protocol_config));
  const [connectivityConfigText, setConnectivityConfigText] = useState<string>(pretty(initial?.connectivity_config));

  const carrierQuery = useQuery({
    queryKey: ["carrier-integrations"],
    queryFn: () => listCarrierIntegrations(),
  });
  const carrierOptions = carrierQuery.data?.integrations ?? [];

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: TransportCreatePayload = {
        ingestion_protocol: ingestionProtocol,
        physical_connectivity: physicalConnectivity || undefined,
        protocol_config: parseJsonObject(protocolConfigText),
        connectivity_config: parseJsonObject(connectivityConfigText),
        is_primary: isPrimary,
        carrier_integration_id: carrierIntegrationId ? Number(carrierIntegrationId) : undefined,
      };
      return createDeviceTransport(deviceId, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-transports", deviceId] });
      toast.success("Transport added");
      setOpen(false);
      onDone();
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to add transport"),
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!initial) throw new Error("Missing transport");
      const payload: TransportUpdatePayload = {
        physical_connectivity: physicalConnectivity || undefined,
        protocol_config: parseJsonObject(protocolConfigText),
        connectivity_config: parseJsonObject(connectivityConfigText),
        is_primary: isPrimary,
        status,
        carrier_integration_id: carrierIntegrationId ? Number(carrierIntegrationId) : undefined,
      };
      return updateDeviceTransport(deviceId, initial.id, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-transports", deviceId] });
      toast.success("Transport updated");
      setOpen(false);
      onDone();
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to update transport"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant={mode === "create" ? "default" : "outline"}>
          {mode === "create" ? "Add Transport" : "Edit"}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Add Transport" : "Edit Transport"}</DialogTitle>
          <DialogDescription>
            Define how this device connects (protocol + physical connectivity) and any carrier integration link.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2 md:grid-cols-2">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Ingestion Protocol</div>
              <Select
                value={ingestionProtocol}
                onValueChange={(v) => {
                  if (mode === "edit") return; // not editable on update
                  setIngestionProtocol(v);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select protocol" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(protocolLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {mode === "edit" && (
                <div className="text-xs text-muted-foreground">Protocol is not editable after creation.</div>
              )}
            </div>

            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Physical Connectivity</div>
              <Select value={physicalConnectivity} onValueChange={setPhysicalConnectivity}>
                <SelectTrigger>
                  <SelectValue placeholder="Select connectivity (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">(none)</SelectItem>
                  {Object.entries(connectivityLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Carrier Integration</div>
              <Select value={carrierIntegrationId} onValueChange={setCarrierIntegrationId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select carrier integration (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">(none)</SelectItem>
                  {carrierOptions.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end gap-3">
              <div className="flex items-center gap-2">
                <Switch
                  id="primary-transport"
                  checked={isPrimary}
                  onCheckedChange={setIsPrimary}
                />
                <Label htmlFor="primary-transport" className="text-sm">
                  Primary transport
                </Label>
              </div>

              {mode === "edit" && (
                <div className="flex-1 space-y-1">
                  <div className="text-sm text-muted-foreground">Status</div>
                  <Select value={status} onValueChange={setStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">active</SelectItem>
                      <SelectItem value="inactive">inactive</SelectItem>
                      <SelectItem value="failover">failover</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Protocol Config (JSON)</div>
              <Textarea
                className="font-mono"
                rows={8}
                value={protocolConfigText}
                onChange={(e) => setProtocolConfigText(e.target.value)}
                placeholder='{"client_id":"...","topic_prefix":"..."}'
              />
            </div>
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Connectivity Config (JSON)</div>
              <Textarea
                className="font-mono"
                rows={8}
                value={connectivityConfigText}
                onChange={(e) => setConnectivityConfigText(e.target.value)}
                placeholder='{"carrier_name":"...","apn":"..."}'
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={() => {
              if (mode === "create") {
                createMutation.mutate();
              } else {
                updateMutation.mutate();
              }
            }}
            disabled={createMutation.isPending || updateMutation.isPending}
          >
            {mode === "create"
              ? createMutation.isPending
                ? "Adding..."
                : "Add"
              : updateMutation.isPending
                ? "Saving..."
                : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function statusVariant(status: string) {
  const s = (status || "").toLowerCase();
  if (s === "active") return "default";
  if (s === "failover") return "secondary";
  if (s === "inactive") return "outline";
  return "outline";
}

export function DeviceTransportTab({ deviceId }: { deviceId: string }) {
  const queryClient = useQueryClient();
  const transportsQuery = useQuery({
    queryKey: ["device-transports", deviceId],
    queryFn: () => listDeviceTransports(deviceId),
    enabled: !!deviceId,
  });

  const transports = transportsQuery.data ?? [];
  const sorted = useMemo(() => {
    return [...transports].sort((a, b) => Number(b.is_primary) - Number(a.is_primary));
  }, [transports]);

  const deleteMutation = useMutation({
    mutationFn: async (transportId: number) => deleteDeviceTransport(deviceId, transportId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-transports", deviceId] });
      toast.success("Transport deleted");
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to delete transport"),
  });

  return (
    <div className="space-y-4 pt-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">Transport</div>
          <div className="text-sm text-muted-foreground">
            Protocol configuration and physical connectivity (cellular, ethernet, WiFi, etc).
          </div>
        </div>
        <TransportDialog deviceId={deviceId} mode="create" onDone={() => {}} />
      </div>

      {sorted.length === 0 ? (
        <div className="rounded-lg border border-border py-10 text-center text-muted-foreground">
          No transports configured. Add a transport to define how this device connects.
        </div>
      ) : (
        <div className="grid gap-3">
          {sorted.map((t) => (
            <div key={t.id} className="rounded border border-border p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{protocolLabels[t.ingestion_protocol] ?? t.ingestion_protocol}</Badge>
                    {t.physical_connectivity && (
                      <Badge variant="outline">
                        {connectivityLabels[t.physical_connectivity] ?? t.physical_connectivity}
                      </Badge>
                    )}
                    <Badge variant={statusVariant(t.status)}>{t.status}</Badge>
                    {t.is_primary && <Badge>primary</Badge>}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Last connected: {t.last_connected_at ? new Date(t.last_connected_at).toLocaleString() : "—"}
                  </div>
                  {t.carrier_integration && (
                    <div className="text-sm">
                      Carrier integration:{" "}
                      <a className="underline" href="/app/settings/carrier">
                        {t.carrier_integration.display_name}
                      </a>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <TransportDialog deviceId={deviceId} mode="edit" initial={t} onDone={() => {}} />
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button size="sm" variant="outline">
                        Delete
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete transport?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This removes the transport configuration for this device.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deleteMutation.mutate(t.id)}
                          disabled={deleteMutation.isPending}
                        >
                          {deleteMutation.isPending ? "Deleting..." : "Delete"}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>

              <details className="rounded border border-border bg-muted/10 p-3">
                <summary className="cursor-pointer text-sm font-medium">Protocol config</summary>
                <pre className="mt-2 max-h-64 overflow-auto rounded bg-background p-2 text-xs">
                  {pretty(t.protocol_config)}
                </pre>
              </details>

              <details className="rounded border border-border bg-muted/10 p-3">
                <summary className="cursor-pointer text-sm font-medium">Connectivity config</summary>
                <pre className="mt-2 max-h-64 overflow-auto rounded bg-background p-2 text-xs">
                  {pretty(t.connectivity_config)}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


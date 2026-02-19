import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getErrorMessage } from "@/lib/errors";
import {
  getDeviceConnection,
  upsertDeviceConnection,
} from "@/services/api/sensors";
import type { ConnectionUpsert, DeviceConnection } from "@/services/api/types";

interface DeviceConnectionPanelProps {
  deviceId: string;
}

const CONNECTION_TYPES = ["cellular", "ethernet", "wifi", "lora", "satellite", "other"] as const;
const SIM_STATUSES = ["active", "suspended", "deactivated", "ready", "unknown"] as const;

function dotClass(kind: "good" | "bad" | "neutral"): string {
  if (kind === "good") return "bg-status-online";
  if (kind === "bad") return "bg-status-critical";
  return "bg-muted-foreground";
}

function parseOptionalInt(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return undefined;
  return Math.trunc(n);
}

export function DeviceConnectionPanel({ deviceId }: DeviceConnectionPanelProps) {
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["device-connection", deviceId],
    queryFn: () => getDeviceConnection(deviceId),
    enabled: !!deviceId,
  });

  const conn = data?.connection ?? null;

  const upsertMutation = useMutation({
    mutationFn: (payload: ConnectionUpsert) => upsertDeviceConnection(deviceId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-connection", deviceId] });
      toast.success("Connection updated");
      setEditOpen(false);
    },
    onError: (err) => toast.error(getErrorMessage(err) || "Failed to update connection"),
  });

  const usagePct = useMemo(() => {
    if (!conn?.data_limit_mb || conn.data_limit_mb <= 0) return 0;
    if (conn.data_used_mb == null) return 0;
    return (conn.data_used_mb / conn.data_limit_mb) * 100;
  }, [conn?.data_limit_mb, conn?.data_used_mb]);

  const barColor =
    usagePct > 90 ? "bg-status-critical" : usagePct > 75 ? "bg-status-warning" : "bg-status-online";

  const networkDot =
    conn?.network_status === "connected" ? "good" : conn?.network_status === "disconnected" ? "bad" : "neutral";

  const simDot =
    conn?.sim_status === "active" ? "good" : conn?.sim_status === "suspended" ? "bad" : "neutral";

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Connection</h3>
          <p className="text-xs text-muted-foreground">Carrier, SIM, and network diagnostics</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setEditOpen(true)} disabled={isLoading}>
          <Pencil className="mr-1 h-3 w-3" /> {conn ? "Edit" : "Set Up Connection"}
        </Button>
      </div>

      {!conn ? (
        <div className="text-sm text-muted-foreground py-2">No connection configured.</div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Type" value={conn.connection_type} />
            <Stat label="Carrier" value={conn.carrier_name ?? "—"} />
            <Stat
              label="Network"
              value={
                <span className="inline-flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${dotClass(networkDot)}`} aria-hidden="true" />
                  <span className="text-sm font-medium">{conn.network_status ?? "unknown"}</span>
                </span>
              }
            />

            <Stat label="Plan" value={conn.plan_name ?? "—"} />
            <Stat
              label="SIM Status"
              value={
                <span className="inline-flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${dotClass(simDot)}`} aria-hidden="true" />
                  <span className="text-sm font-medium">{conn.sim_status ?? "unknown"}</span>
                </span>
              }
            />
            <Stat label="IP Address" value={conn.ip_address ?? "—"} />
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Data Usage</span>
              <span>
                {conn.data_used_mb != null ? conn.data_used_mb.toFixed(1) : "—"} /{" "}
                {conn.data_limit_mb ?? "—"} MB ({usagePct.toFixed(1)}%)
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div className={`h-full ${barColor}`} style={{ width: `${Math.min(usagePct, 100)}%` }} />
            </div>
            {conn.billing_cycle_start != null && (
              <div className="text-xs text-muted-foreground">
                Billing cycle resets on the {conn.billing_cycle_start}
                {conn.billing_cycle_start === 1
                  ? "st"
                  : conn.billing_cycle_start === 2
                    ? "nd"
                    : conn.billing_cycle_start === 3
                      ? "rd"
                      : "th"}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-xs text-muted-foreground">SIM ICCID</span>
              <div className="font-mono text-sm">{conn.sim_iccid ?? "—"}</div>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">APN</span>
              <div className="text-sm font-medium">{conn.apn ?? "—"}</div>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Last network attach</span>
              <div className="text-sm font-medium">
                {conn.last_network_attach ? new Date(conn.last_network_attach).toLocaleString() : "—"}
              </div>
            </div>
          </div>
        </>
      )}

      <EditConnectionDialog
        open={editOpen}
        setOpen={setEditOpen}
        connection={conn}
        isSubmitting={upsertMutation.isPending}
        onSubmit={(payload) => upsertMutation.mutate(payload)}
      />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border p-2 space-y-1">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium truncate">{value}</div>
    </div>
  );
}

function EditConnectionDialog({
  open,
  setOpen,
  connection,
  isSubmitting,
  onSubmit,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
  connection: DeviceConnection | null;
  isSubmitting: boolean;
  onSubmit: (payload: ConnectionUpsert) => void;
}) {
  const [connectionType, setConnectionType] = useState<string>("cellular");
  const [carrierName, setCarrierName] = useState("");
  const [carrierAccountId, setCarrierAccountId] = useState("");
  const [planName, setPlanName] = useState("");
  const [apn, setApn] = useState("");
  const [simIccid, setSimIccid] = useState("");
  const [simStatus, setSimStatus] = useState<string>("active");
  const [dataLimitMb, setDataLimitMb] = useState("");
  const [billingCycleStart, setBillingCycleStart] = useState("");
  const [ipAddress, setIpAddress] = useState("");
  const [msisdn, setMsisdn] = useState("");

  useEffect(() => {
    if (!open) return;
    setConnectionType(connection?.connection_type ?? "cellular");
    setCarrierName(connection?.carrier_name ?? "");
    setCarrierAccountId(connection?.carrier_account_id ?? "");
    setPlanName(connection?.plan_name ?? "");
    setApn(connection?.apn ?? "");
    setSimIccid(connection?.sim_iccid ?? "");
    setSimStatus(connection?.sim_status ?? "active");
    setDataLimitMb(connection?.data_limit_mb != null ? String(connection.data_limit_mb) : "");
    setBillingCycleStart(
      connection?.billing_cycle_start != null ? String(connection.billing_cycle_start) : "",
    );
    setIpAddress(connection?.ip_address ?? "");
    setMsisdn(connection?.msisdn ?? "");
  }, [open, connection]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Connection</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Connection type</Label>
            <Select value={connectionType} onValueChange={setConnectionType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CONNECTION_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="carrier_name">Carrier name</Label>
              <Input id="carrier_name" value={carrierName} onChange={(e) => setCarrierName(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="carrier_account_id">Carrier account ID</Label>
              <Input
                id="carrier_account_id"
                value={carrierAccountId}
                onChange={(e) => setCarrierAccountId(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="plan_name">Plan name</Label>
              <Input id="plan_name" value={planName} onChange={(e) => setPlanName(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="apn">APN</Label>
              <Input id="apn" value={apn} onChange={(e) => setApn(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="sim_iccid">SIM ICCID</Label>
              <Input id="sim_iccid" value={simIccid} onChange={(e) => setSimIccid(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>SIM status</Label>
              <Select value={simStatus} onValueChange={setSimStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SIM_STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="data_limit_mb">Data limit (MB)</Label>
              <Input
                id="data_limit_mb"
                type="number"
                value={dataLimitMb}
                onChange={(e) => setDataLimitMb(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="billing_cycle_start">Billing cycle start (1-28)</Label>
              <Input
                id="billing_cycle_start"
                type="number"
                value={billingCycleStart}
                onChange={(e) => setBillingCycleStart(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="ip_address">IP address</Label>
              <Input id="ip_address" value={ipAddress} onChange={(e) => setIpAddress(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="msisdn">MSISDN</Label>
              <Input id="msisdn" value={msisdn} onChange={(e) => setMsisdn(e.target.value)} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              const payload: ConnectionUpsert = {
                connection_type: connectionType,
                ...(carrierName.trim() ? { carrier_name: carrierName.trim() } : {}),
                ...(carrierAccountId.trim() ? { carrier_account_id: carrierAccountId.trim() } : {}),
                ...(planName.trim() ? { plan_name: planName.trim() } : {}),
                ...(apn.trim() ? { apn: apn.trim() } : {}),
                ...(simIccid.trim() ? { sim_iccid: simIccid.trim() } : {}),
                ...(simStatus ? { sim_status: simStatus } : {}),
                ...(parseOptionalInt(dataLimitMb) != null ? { data_limit_mb: parseOptionalInt(dataLimitMb) } : {}),
                ...(parseOptionalInt(billingCycleStart) != null
                  ? { billing_cycle_start: parseOptionalInt(billingCycleStart) }
                  : {}),
                ...(ipAddress.trim() ? { ip_address: ipAddress.trim() } : {}),
                ...(msisdn.trim() ? { msisdn: msisdn.trim() } : {}),
              };
              onSubmit(payload);
            }}
            disabled={isSubmitting}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


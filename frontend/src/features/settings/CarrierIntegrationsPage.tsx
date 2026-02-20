import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Plus, TriangleAlert, XCircle } from "lucide-react";

import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import {
  createCarrierIntegration,
  deleteCarrierIntegration,
  listCarrierIntegrations,
  updateCarrierIntegration,
} from "@/services/api/carrier";
import { getEntitlements } from "@/services/api/billing";
import type {
  CarrierIntegration,
  CarrierIntegrationCreate,
  CarrierIntegrationUpdate,
} from "@/services/api/types";
import { getErrorMessage } from "@/lib/errors";

const CARRIER_OPTIONS = ["hologram", "1nce"] as const;
const SYNC_INTERVALS = [15, 30, 60, 120, 360] as const;

export default function CarrierIntegrationsPage({ embedded }: { embedded?: boolean }) {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CarrierIntegration | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CarrierIntegration | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["carrier-integrations"],
    queryFn: listCarrierIntegrations,
  });

  const entitlements = useQuery({
    queryKey: ["entitlements"],
    queryFn: getEntitlements,
  });
  const isSelfService = entitlements.data?.features?.carrier_self_service ?? false;

  const integrations = data?.integrations ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: CarrierIntegrationCreate) => createCarrierIntegration(payload),
    onSuccess: async () => {
      toast.success("Carrier integration created");
      setAddOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["carrier-integrations"] });
    },
    onError: (err) => toast.error(getErrorMessage(err) || "Failed to create integration"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CarrierIntegrationUpdate }) =>
      updateCarrierIntegration(id, payload),
    onSuccess: async () => {
      toast.success("Carrier integration updated");
      setEditTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["carrier-integrations"] });
    },
    onError: (err) => toast.error(getErrorMessage(err) || "Failed to update integration"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteCarrierIntegration(id),
    onSuccess: async () => {
      toast.success("Carrier integration deleted");
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["carrier-integrations"] });
    },
    onError: (err) => toast.error(getErrorMessage(err) || "Failed to delete integration"),
  });

  const actions = isSelfService ? (
    <Button size="sm" variant="outline" onClick={() => setAddOpen(true)}>
      <Plus className="mr-1 h-3 w-3" /> Add Carrier
    </Button>
  ) : null;

  return (
    <div className="space-y-4">
      {!embedded ? (
        <PageHeader
          title="Carrier Integrations"
          description="Connect your IoT carrier accounts for diagnostics and usage"
          action={actions}
        />
      ) : actions ? (
        <div className="flex justify-end gap-2 mb-4">{actions}</div>
      ) : null}

      {!isSelfService && (
        <Card className="border-muted">
          <CardContent className="p-4 text-sm flex items-start gap-2">
            <TriangleAlert className="mt-0.5 h-4 w-4 text-muted-foreground" />
            <div className="text-muted-foreground">
              Carrier integrations are managed by your service provider. Contact support to make changes.
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">Loading…</div>
          </CardContent>
        </Card>
      ) : integrations.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <div className="text-sm text-muted-foreground">
              No carrier integrations configured yet.
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {integrations.map((i) => (
            <Card key={i.id} className={i.enabled ? "" : "opacity-75"}>
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${i.enabled ? "bg-status-online" : "bg-muted-foreground"}`} />
                    <span>{i.display_name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {i.carrier_name}
                    </Badge>
                  </CardTitle>
                  <div className="text-xs text-muted-foreground">
                    Account: {i.account_id ?? "—"}
                  </div>
                </div>

                <div className="flex gap-2">
                  {isSelfService ? (
                    <>
                      <Button size="sm" variant="outline" onClick={() => setEditTarget(i)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-destructive"
                        onClick={() => setDeleteTarget(i)}
                      >
                        Delete
                      </Button>
                    </>
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                  <Info label="API Key" value={i.api_key_masked ?? "—"} mono />
                  <Info label="Sync" value={i.sync_enabled ? `Every ${i.sync_interval_minutes} min` : "Disabled"} />
                  <Info label="Last sync" value={formatLastSync(i)} />
                  <Info label="Status" value={<SyncStatusBadge integration={i} />} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <IntegrationDialog
        title="Add Carrier Integration"
        open={addOpen}
        setOpen={setAddOpen}
        submitting={createMutation.isPending}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />

      <IntegrationDialog
        title="Edit Carrier Integration"
        open={!!editTarget}
        setOpen={(o) => !o && setEditTarget(null)}
        submitting={updateMutation.isPending}
        integration={editTarget}
        onSubmit={(payload) => {
          if (!editTarget) return;
          updateMutation.mutate({ id: editTarget.id, payload });
        }}
      />

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete carrier integration</AlertDialogTitle>
            <AlertDialogDescription>
              Deleting this integration will unlink all devices connected to it. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending || !deleteTarget}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function Info({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="rounded-md border border-border p-2 space-y-1">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-sm font-medium truncate ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}

function formatLastSync(i: CarrierIntegration) {
  if (!i.last_sync_at) return "Never";
  try {
    return new Date(i.last_sync_at).toLocaleString();
  } catch {
    return i.last_sync_at;
  }
}

function SyncStatusBadge({ integration }: { integration: CarrierIntegration }) {
  const status = integration.last_sync_status || "never";
  if (status === "success") {
    return (
      <span className="inline-flex items-center gap-1 text-status-online">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        success
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="inline-flex items-center gap-1 text-status-warning">
        <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
        partial
      </span>
    );
  }
  if (status === "error") {
    const msg = integration.last_sync_error || "Sync error";
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex items-center gap-1 text-status-critical cursor-help">
              <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
              error
            </span>
          </TooltipTrigger>
          <TooltipContent side="top">{msg}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }
  return <span className="text-muted-foreground">never</span>;
}

function IntegrationDialog({
  title,
  open,
  setOpen,
  submitting,
  integration,
  onSubmit,
}: {
  title: string;
  open: boolean;
  setOpen: (open: boolean) => void;
  submitting: boolean;
  integration?: CarrierIntegration | null;
  onSubmit: (payload: any) => void;
}) {
  const isEditing = !!integration;
  const [carrierName, setCarrierName] = useState<string>(CARRIER_OPTIONS[0]);
  const [displayName, setDisplayName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [accountId, setAccountId] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [syncEnabled, setSyncEnabled] = useState(true);
  const [syncInterval, setSyncInterval] = useState<number>(60);

  useEffect(() => {
    if (!open) return;
    setCarrierName(integration?.carrier_name ?? CARRIER_OPTIONS[0]);
    setDisplayName(integration?.display_name ?? "");
    setApiKey("");
    setApiSecret("");
    setAccountId(integration?.account_id ?? "");
    setApiBaseUrl("");
    setSyncEnabled(integration?.sync_enabled ?? true);
    setSyncInterval(integration?.sync_interval_minutes ?? 60);
  }, [open, integration]);

  const canSubmit = useMemo(() => {
    if (!displayName.trim()) return false;
    if (!carrierName) return false;
    if (!isEditing && !apiKey.trim()) return false;
    return true;
  }, [displayName, carrierName, apiKey, isEditing]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>Configure a carrier API integration for diagnostics and usage sync.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Carrier</Label>
            <Select value={carrierName} onValueChange={setCarrierName} disabled={isEditing}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CARRIER_OPTIONS.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label htmlFor="display_name">Display name</Label>
            <Input id="display_name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>

          <div className="space-y-1">
            <Label htmlFor="api_key">API key</Label>
            <Input
              id="api_key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={isEditing ? "Leave blank to keep existing" : ""}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="api_secret">API secret (optional)</Label>
            <Input
              id="api_secret"
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder={isEditing ? "Leave blank to keep existing" : ""}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="account_id">Account ID (optional)</Label>
            <Input id="account_id" value={accountId} onChange={(e) => setAccountId(e.target.value)} />
          </div>

          <div className="space-y-1">
            <Label htmlFor="api_base_url">Custom API URL (optional)</Label>
            <Input id="api_base_url" value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="sync_enabled">Sync enabled</Label>
            <Switch id="sync_enabled" checked={syncEnabled} onCheckedChange={setSyncEnabled} />
          </div>

          <div className="space-y-1">
            <Label>Sync interval</Label>
            <Select value={String(syncInterval)} onValueChange={(v) => setSyncInterval(Number(v))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SYNC_INTERVALS.map((m) => (
                  <SelectItem key={m} value={String(m)}>
                    Every {m} min
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit || submitting}
            onClick={() => {
              if (isEditing && integration) {
                const payload: CarrierIntegrationUpdate = {
                  display_name: displayName.trim(),
                  enabled: true,
                  sync_enabled: syncEnabled,
                  sync_interval_minutes: syncInterval,
                  ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
                  ...(apiSecret.trim() ? { api_secret: apiSecret.trim() } : {}),
                  ...(accountId.trim() ? { account_id: accountId.trim() } : {}),
                  ...(apiBaseUrl.trim() ? { api_base_url: apiBaseUrl.trim() } : {}),
                };
                onSubmit(payload);
              } else {
                const payload: CarrierIntegrationCreate = {
                  carrier_name: carrierName,
                  display_name: displayName.trim(),
                  api_key: apiKey.trim(),
                  ...(apiSecret.trim() ? { api_secret: apiSecret.trim() } : {}),
                  ...(accountId.trim() ? { account_id: accountId.trim() } : {}),
                  ...(apiBaseUrl.trim() ? { api_base_url: apiBaseUrl.trim() } : {}),
                  sync_enabled: syncEnabled,
                  sync_interval_minutes: syncInterval,
                  config: {},
                };
                onSubmit(payload);
              }
            }}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


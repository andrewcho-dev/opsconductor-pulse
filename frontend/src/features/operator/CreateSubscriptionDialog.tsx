"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import { apiGet } from "@/services/api/client";
import {
  createDeviceSubscription,
  fetchOperatorDevices,
} from "@/services/api/operator";
import { fetchDevicePlans } from "@/services/api/device-tiers";

interface TenantRow {
  tenant_id: string;
  name: string;
}

interface TenantListResponse {
  tenants: TenantRow[];
}

interface CreateSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
  preselectedTenantId?: string;
}

export function CreateSubscriptionDialog({
  open,
  onOpenChange,
  onCreated,
  preselectedTenantId,
}: CreateSubscriptionDialogProps) {
  const [tenantId, setTenantId] = useState(preselectedTenantId ?? "");
  const [deviceId, setDeviceId] = useState("");
  const [planId, setPlanId] = useState("");
  const [termEnd, setTermEnd] = useState("");

  useEffect(() => {
    if (!open) return;
    setTenantId(preselectedTenantId ?? "");
    setDeviceId("");
    setPlanId("");
    setTermEnd("");
  }, [open, preselectedTenantId]);

  const { data: tenantData } = useQuery({
    queryKey: ["operator-tenants"],
    queryFn: () => apiGet<TenantListResponse>("/operator/tenants?status=ALL&limit=500"),
    enabled: open && !preselectedTenantId,
  });

  const { data: deviceData, isLoading: devicesLoading } = useQuery({
    queryKey: ["operator-tenant-devices", tenantId],
    queryFn: () => fetchOperatorDevices(tenantId, 500, 0),
    enabled: open && !!tenantId,
  });

  const { data: planData, isLoading: plansLoading } = useQuery({
    queryKey: ["operator-device-plans"],
    queryFn: fetchDevicePlans,
    enabled: open,
  });

  const tenantOptions = tenantData?.tenants ?? [];
  const deviceOptions = deviceData?.devices ?? [];
  const planOptions = planData?.plans ?? [];

  const canSubmit = useMemo(() => {
    return Boolean(tenantId && deviceId && planId);
  }, [tenantId, deviceId, planId]);

  const mutation = useMutation({
    mutationFn: async () => {
      return createDeviceSubscription({
        tenant_id: tenantId,
        device_id: deviceId,
        plan_id: planId,
        status: "ACTIVE",
        term_end: termEnd ? new Date(termEnd).toISOString() : undefined,
      });
    },
    onSuccess: () => {
      toast.success("Device subscription created");
      onCreated?.();
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to create subscription");
    },
  });

  // When tenant changes, clear dependent selections.
  useEffect(() => {
    setDeviceId("");
  }, [tenantId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Device Subscription</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {!preselectedTenantId && (
            <div className="space-y-2">
              <span className="text-sm font-medium">Tenant</span>
              <Select value={tenantId} onValueChange={setTenantId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select tenant" />
                </SelectTrigger>
                <SelectContent>
                  {tenantOptions.map((t) => (
                    <SelectItem key={t.tenant_id} value={t.tenant_id}>
                      {t.name} ({t.tenant_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <span className="text-sm font-medium">Device</span>
            <Select
              value={deviceId}
              onValueChange={setDeviceId}
              disabled={!tenantId || devicesLoading}
            >
              <SelectTrigger>
                <SelectValue placeholder={devicesLoading ? "Loading devices..." : "Select device"} />
              </SelectTrigger>
              <SelectContent>
                {deviceOptions.map((d) => (
                  <SelectItem key={d.device_id} value={d.device_id}>
                    {d.device_id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Plan</span>
            <Select value={planId} onValueChange={setPlanId} disabled={plansLoading}>
              <SelectTrigger>
                <SelectValue placeholder={plansLoading ? "Loading plans..." : "Select plan"} />
              </SelectTrigger>
              <SelectContent>
                {planOptions.map((p) => (
                  <SelectItem key={p.plan_id} value={p.plan_id}>
                    {p.name} ({p.plan_id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Term End (optional)</span>
            <Input
              type="date"
              value={termEnd}
              onChange={(e) => setTermEnd(e.target.value)}
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            {(mutation.error as Error).message}
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit || mutation.isPending}
          >
            {mutation.isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


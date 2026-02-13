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
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiGet, apiPost } from "@/services/api/client";

interface DeviceRow {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
}

interface DeviceListResponse {
  devices: DeviceRow[];
}

interface SubscriptionRow {
  subscription_id: string;
  device_limit: number;
  active_device_count: number;
  status: string;
}

interface SubscriptionListResponse {
  subscriptions: SubscriptionRow[];
}

interface BulkAssignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenantId: string;
  onComplete: () => void;
}

export function BulkAssignDialog({
  open,
  onOpenChange,
  tenantId,
  onComplete,
}: BulkAssignDialogProps) {
  const [targetSubscriptionId, setTargetSubscriptionId] = useState("");
  const [notes, setNotes] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      setTargetSubscriptionId("");
      setNotes("");
      setSearch("");
      setSelected([]);
    }
  }, [open]);

  const { data: deviceData } = useQuery({
    queryKey: ["operator-unassigned-devices", tenantId],
    queryFn: () =>
      apiGet<DeviceListResponse>(
        `/operator/tenants/${tenantId}/devices?unassigned=true`
      ),
    enabled: open,
  });

  const { data: subscriptionData } = useQuery({
    queryKey: ["operator-tenant-subscriptions", tenantId],
    queryFn: () =>
      apiGet<SubscriptionListResponse>(
        `/operator/subscriptions?tenant_id=${tenantId}&status=ACTIVE&limit=200`
      ),
    enabled: open,
  });

  const devices = deviceData?.devices ?? [];
  const subscriptions = subscriptionData?.subscriptions ?? [];
  const selectedSubscription = subscriptions.find(
    (sub) => sub.subscription_id === targetSubscriptionId
  );
  const availableSlots = selectedSubscription
    ? Math.max(
        0,
        selectedSubscription.device_limit - selectedSubscription.active_device_count
      )
    : 0;

  const filteredDevices = useMemo(() => {
    if (!search.trim()) return devices;
    const term = search.toLowerCase();
    return devices.filter(
      (device) =>
        device.device_id.toLowerCase().includes(term) ||
        device.site_id.toLowerCase().includes(term)
    );
  }, [devices, search]);

  useEffect(() => {
    if (selected.length > availableSlots) {
      setSelected((prev) => prev.slice(0, availableSlots));
    }
  }, [availableSlots, selected.length]);

  const mutation = useMutation({
    mutationFn: async () => {
      for (const deviceId of selected) {
        await apiPost(`/operator/devices/${deviceId}/subscription`, {
          subscription_id: targetSubscriptionId,
          notes,
        });
      }
    },
    onSuccess: () => {
      onComplete();
    },
  });

  const toggleDevice = (deviceId: string, checked: boolean) => {
    if (checked) {
      if (selected.length >= availableSlots) {
        return;
      }
      setSelected((prev) => [...prev, deviceId]);
    } else {
      setSelected((prev) => prev.filter((id) => id !== deviceId));
    }
  };

  const selectAll = () => {
    if (availableSlots === 0) {
      setSelected([]);
      return;
    }
    const ids = filteredDevices.map((device) => device.device_id);
    setSelected(ids.slice(0, availableSlots));
  };

  const canSubmit =
    targetSubscriptionId &&
    notes.trim().length > 0 &&
    selected.length > 0 &&
    availableSlots > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Bulk Assign Devices</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <span className="text-sm font-medium">Target Subscription</span>
            <Select value={targetSubscriptionId} onValueChange={setTargetSubscriptionId}>
              <SelectTrigger>
                <SelectValue placeholder="Select subscription" />
              </SelectTrigger>
              <SelectContent>
                {subscriptions.map((sub) => (
                  <SelectItem key={sub.subscription_id} value={sub.subscription_id}>
                    {sub.subscription_id} ({sub.active_device_count}/{sub.device_limit})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedSubscription && (
              <div className="text-xs text-muted-foreground">
                Available slots: {availableSlots}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="w-64"
              placeholder="Search devices"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <Button variant="outline" size="sm" onClick={selectAll}>
              Select All (max {availableSlots})
            </Button>
            <Badge variant="outline">
              {selected.length} / {availableSlots} selected
            </Badge>
          </div>

          <ScrollArea className="max-h-60 rounded-md border p-2">
            <div className="space-y-2">
              {filteredDevices.length === 0 && (
                <div className="text-sm text-muted-foreground">
                  No unassigned devices found.
                </div>
              )}
              {filteredDevices.map((device) => (
                <label
                  key={device.device_id}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={selected.includes(device.device_id)}
                      onCheckedChange={(checked) =>
                        toggleDevice(device.device_id, Boolean(checked))
                      }
                      disabled={
                        !selected.includes(device.device_id) &&
                        selected.length >= availableSlots
                      }
                    />
                    <span className="font-mono">{device.device_id}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {device.site_id}
                  </div>
                </label>
              ))}
            </div>
          </ScrollArea>

          <div className="space-y-2">
            <span className="text-sm font-medium">Notes</span>
            <Textarea
              placeholder="Reason for assignment (required)"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
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
            {mutation.isPending ? "Assigning..." : "Assign Devices"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

# 007: Frontend Device-to-Subscription Assignment

## Task

Create UI components for assigning devices to subscriptions.

## Files to Create

1. `frontend/src/features/operator/DeviceSubscriptionDialog.tsx`
2. `frontend/src/features/operator/BulkAssignDialog.tsx`

## 1. DeviceSubscriptionDialog.tsx

Dialog to assign a single device to a subscription.

```tsx
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { apiGet, apiPost } from "@/services/api/client";
import { AlertTriangle } from "lucide-react";

interface Subscription {
  subscription_id: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
  status: string;
  term_end: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceId: string;
  tenantId: string;
  currentSubscriptionId: string | null;
  onAssigned: () => void;
}

export function DeviceSubscriptionDialog({
  open, onOpenChange, deviceId, tenantId, currentSubscriptionId, onAssigned
}: Props) {
  const [selectedSubscription, setSelectedSubscription] = useState<string>("");
  const [notes, setNotes] = useState("");

  // Fetch available subscriptions for this tenant
  const { data: subsData } = useQuery({
    queryKey: ["tenant-subscriptions", tenantId],
    queryFn: () => apiGet<{ subscriptions: Subscription[] }>(
      `/operator/subscriptions?tenant_id=${tenantId}&status=ACTIVE`
    ),
    enabled: open,
  });

  const subscriptions = subsData?.subscriptions || [];

  const mutation = useMutation({
    mutationFn: async () => {
      return apiPost(`/operator/devices/${deviceId}/subscription`, {
        subscription_id: selectedSubscription,
        notes,
      });
    },
    onSuccess: () => {
      onAssigned();
      onOpenChange(false);
    },
  });

  const selectedSub = subscriptions.find(s => s.subscription_id === selectedSubscription);
  const isAtLimit = selectedSub && selectedSub.active_device_count >= selectedSub.device_limit;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Device to Subscription</DialogTitle>
          <DialogDescription>
            Device: <code className="bg-muted px-1">{deviceId}</code>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {currentSubscriptionId && (
            <div className="rounded-md bg-muted p-3">
              <p className="text-sm">
                Current subscription:{" "}
                <code className="font-mono">{currentSubscriptionId}</code>
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label>Target Subscription</Label>
            <Select value={selectedSubscription} onValueChange={setSelectedSubscription}>
              <SelectTrigger>
                <SelectValue placeholder="Select subscription..." />
              </SelectTrigger>
              <SelectContent>
                {subscriptions.map((sub) => {
                  const available = sub.device_limit - sub.active_device_count;
                  const isCurrent = sub.subscription_id === currentSubscriptionId;
                  return (
                    <SelectItem
                      key={sub.subscription_id}
                      value={sub.subscription_id}
                      disabled={isCurrent || available <= 0}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs">{sub.subscription_id}</span>
                        <Badge variant="outline" className="text-xs">
                          {sub.subscription_type}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          ({sub.active_device_count}/{sub.device_limit})
                        </span>
                        {isCurrent && (
                          <span className="text-xs text-muted-foreground">(current)</span>
                        )}
                        {available <= 0 && !isCurrent && (
                          <span className="text-xs text-destructive">(full)</span>
                        )}
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          {isAtLimit && (
            <div className="flex items-center gap-2 text-sm text-orange-600">
              <AlertTriangle className="h-4 w-4" />
              This subscription is at its device limit
            </div>
          )}

          <div className="space-y-2">
            <Label>Notes (required for audit)</Label>
            <Textarea
              placeholder="Reason for this assignment..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!selectedSubscription || !notes || mutation.isPending || isAtLimit}
          >
            {mutation.isPending ? "Assigning..." : "Assign Device"}
          </Button>
        </DialogFooter>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            Error: {(mutation.error as Error).message}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

## 2. BulkAssignDialog.tsx

Dialog to assign multiple devices to a subscription at once.

```tsx
import { useState, useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { apiGet, apiPost } from "@/services/api/client";
import { Search } from "lucide-react";

interface Device {
  device_id: string;
  site_id: string;
  subscription_id: string | null;
}

interface Subscription {
  subscription_id: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenantId: string;
  onComplete: () => void;
}

export function BulkAssignDialog({ open, onOpenChange, tenantId, onComplete }: Props) {
  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [targetSubscription, setTargetSubscription] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [notes, setNotes] = useState("");

  // Fetch devices without subscription
  const { data: devicesData } = useQuery({
    queryKey: ["unassigned-devices", tenantId],
    queryFn: () => apiGet<{ devices: Device[] }>(
      `/operator/tenants/${tenantId}/devices?unassigned=true`
    ),
    enabled: open,
  });

  // Fetch subscriptions
  const { data: subsData } = useQuery({
    queryKey: ["tenant-subscriptions", tenantId],
    queryFn: () => apiGet<{ subscriptions: Subscription[] }>(
      `/operator/subscriptions?tenant_id=${tenantId}&status=ACTIVE`
    ),
    enabled: open,
  });

  const devices = devicesData?.devices || [];
  const subscriptions = subsData?.subscriptions || [];

  const filteredDevices = useMemo(() => {
    if (!searchQuery) return devices;
    const q = searchQuery.toLowerCase();
    return devices.filter(d =>
      d.device_id.toLowerCase().includes(q) ||
      d.site_id.toLowerCase().includes(q)
    );
  }, [devices, searchQuery]);

  const targetSub = subscriptions.find(s => s.subscription_id === targetSubscription);
  const availableSlots = targetSub
    ? targetSub.device_limit - targetSub.active_device_count
    : 0;

  const toggleDevice = (deviceId: string) => {
    setSelectedDevices(prev => {
      const next = new Set(prev);
      if (next.has(deviceId)) {
        next.delete(deviceId);
      } else if (next.size < availableSlots) {
        next.add(deviceId);
      }
      return next;
    });
  };

  const selectAll = () => {
    const toSelect = filteredDevices.slice(0, availableSlots);
    setSelectedDevices(new Set(toSelect.map(d => d.device_id)));
  };

  const mutation = useMutation({
    mutationFn: async () => {
      // Assign each device sequentially
      for (const deviceId of selectedDevices) {
        await apiPost(`/operator/devices/${deviceId}/subscription`, {
          subscription_id: targetSubscription,
          notes,
        });
      }
    },
    onSuccess: () => {
      onComplete();
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Bulk Assign Devices</DialogTitle>
          <DialogDescription>
            Assign multiple devices to a subscription at once
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4 flex-1 overflow-hidden flex flex-col">
          <div className="space-y-2">
            <Label>Target Subscription</Label>
            <Select value={targetSubscription} onValueChange={setTargetSubscription}>
              <SelectTrigger>
                <SelectValue placeholder="Select subscription..." />
              </SelectTrigger>
              <SelectContent>
                {subscriptions.map((sub) => {
                  const available = sub.device_limit - sub.active_device_count;
                  return (
                    <SelectItem key={sub.subscription_id} value={sub.subscription_id}>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs">{sub.subscription_id}</span>
                        <Badge variant="outline">{sub.subscription_type}</Badge>
                        <span className="text-muted-foreground">
                          {available} slots available
                        </span>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          {targetSubscription && (
            <>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search devices..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8"
                  />
                </div>
                <Button variant="outline" size="sm" onClick={selectAll}>
                  Select All ({Math.min(filteredDevices.length, availableSlots)})
                </Button>
                <Button variant="outline" size="sm" onClick={() => setSelectedDevices(new Set())}>
                  Clear
                </Button>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {filteredDevices.length} unassigned devices
                </span>
                <Badge variant={selectedDevices.size === availableSlots ? "default" : "outline"}>
                  {selectedDevices.size} / {availableSlots} selected
                </Badge>
              </div>

              <ScrollArea className="flex-1 border rounded-md">
                <div className="p-2 space-y-1">
                  {filteredDevices.map((device) => {
                    const isSelected = selectedDevices.has(device.device_id);
                    const isDisabled = !isSelected && selectedDevices.size >= availableSlots;
                    return (
                      <div
                        key={device.device_id}
                        className={`flex items-center gap-3 p-2 rounded cursor-pointer ${
                          isSelected ? "bg-primary/10" : isDisabled ? "opacity-50" : "hover:bg-muted"
                        }`}
                        onClick={() => !isDisabled && toggleDevice(device.device_id)}
                      >
                        <Checkbox checked={isSelected} disabled={isDisabled} />
                        <div>
                          <div className="font-mono text-sm">{device.device_id}</div>
                          <div className="text-xs text-muted-foreground">
                            Site: {device.site_id}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </>
          )}

          <div className="space-y-2">
            <Label>Notes (required)</Label>
            <Textarea
              placeholder="Reason for this bulk assignment..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={selectedDevices.size === 0 || !notes || mutation.isPending}
          >
            {mutation.isPending
              ? `Assigning ${selectedDevices.size} devices...`
              : `Assign ${selectedDevices.size} Devices`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## 3. Add to Device Table

In operator device views, add a column showing subscription and an action to reassign:

```tsx
// In device table row:
<TableCell>
  {device.subscription_id ? (
    <code className="text-xs">{device.subscription_id}</code>
  ) : (
    <Badge variant="outline" className="text-orange-600">Unassigned</Badge>
  )}
</TableCell>
<TableCell>
  <Button
    variant="ghost"
    size="sm"
    onClick={() => openAssignDialog(device)}
  >
    {device.subscription_id ? "Reassign" : "Assign"}
  </Button>
</TableCell>
```

## Backend Endpoint Needed

Add endpoint to list unassigned devices:

```python
@router.get("/tenants/{tenant_id}/devices")
async def list_tenant_devices(
    tenant_id: str,
    unassigned: bool = Query(False),
):
    """List devices for a tenant, optionally filtering to unassigned only."""
    # If unassigned=true, filter WHERE subscription_id IS NULL
```

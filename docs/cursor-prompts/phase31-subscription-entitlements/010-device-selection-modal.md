# 010: Device Selection Modal for Downgrade

## Task

Create a modal component that allows users to select which devices to keep when reducing their device limit (downgrading).

## Context

When a tenant renews with a lower device limit, they must select which devices to keep active. The remaining devices will be marked as INACTIVE and stop sending telemetry.

## File to Create

`frontend/src/features/subscription/DeviceSelectionModal.tsx`

## Component Requirements

### Props

```typescript
interface DeviceSelectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentDeviceCount: number;  // e.g., 50 current devices
  newDeviceLimit: number;      // e.g., 30 new limit
  onConfirm: (selectedDeviceIds: string[]) => void;
}
```

### Features

1. Display list of all active devices with checkboxes
2. Show how many devices must be selected (equal to new limit)
3. Counter showing "X of Y selected"
4. Disable confirm button until exact number is selected
5. Search/filter devices by ID, site, or tags
6. Show warning about devices that will be deactivated

## Implementation

```tsx
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, AlertTriangle, Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { apiGet } from "@/services/api/client";

interface Device {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
  tags?: string[];
}

interface DeviceSelectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentDeviceCount: number;
  newDeviceLimit: number;
  onConfirm: (selectedDeviceIds: string[]) => void;
}

export function DeviceSelectionModal({
  open,
  onOpenChange,
  currentDeviceCount,
  newDeviceLimit,
  onConfirm,
}: DeviceSelectionModalProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");

  const { data: devicesData, isLoading } = useQuery({
    queryKey: ["devices-for-selection"],
    queryFn: () =>
      apiGet<{ devices: Device[] }>("/customer/devices?limit=1000"),
    enabled: open,
  });

  const devices = devicesData?.devices ?? [];
  const devicesToDeactivate = currentDeviceCount - newDeviceLimit;

  // Filter devices by search query
  const filteredDevices = useMemo(() => {
    if (!searchQuery.trim()) return devices;
    const query = searchQuery.toLowerCase();
    return devices.filter(
      (d) =>
        d.device_id.toLowerCase().includes(query) ||
        d.site_id.toLowerCase().includes(query) ||
        d.tags?.some((t) => t.toLowerCase().includes(query))
    );
  }, [devices, searchQuery]);

  const toggleDevice = (deviceId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(deviceId)) {
        next.delete(deviceId);
      } else {
        // Only allow selecting up to the new limit
        if (next.size < newDeviceLimit) {
          next.add(deviceId);
        }
      }
      return next;
    });
  };

  const selectAll = () => {
    // Select first N devices (up to limit)
    const toSelect = filteredDevices.slice(0, newDeviceLimit);
    setSelectedIds(new Set(toSelect.map((d) => d.device_id)));
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const handleConfirm = () => {
    onConfirm(Array.from(selectedIds));
    onOpenChange(false);
  };

  const isExactCount = selectedIds.size === newDeviceLimit;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Devices to Keep</DialogTitle>
          <DialogDescription>
            Your new plan allows {newDeviceLimit} devices. Select exactly{" "}
            {newDeviceLimit} devices to keep active.
          </DialogDescription>
        </DialogHeader>

        <Alert className="bg-orange-50 border-orange-200">
          <AlertTriangle className="h-4 w-4 text-orange-600" />
          <AlertDescription className="text-orange-800">
            {devicesToDeactivate} device{devicesToDeactivate !== 1 ? "s" : ""}{" "}
            will be deactivated. Deactivated devices will stop sending telemetry
            but their historical data will be retained.
          </AlertDescription>
        </Alert>

        <div className="flex items-center gap-2 py-2">
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
            Select First {newDeviceLimit}
          </Button>
          <Button variant="outline" size="sm" onClick={clearSelection}>
            Clear
          </Button>
        </div>

        <div className="flex items-center justify-between py-2 text-sm">
          <span className="text-muted-foreground">
            Showing {filteredDevices.length} devices
          </span>
          <Badge
            variant={isExactCount ? "default" : "outline"}
            className={isExactCount ? "bg-green-600" : ""}
          >
            {selectedIds.size} / {newDeviceLimit} selected
          </Badge>
        </div>

        <ScrollArea className="flex-1 border rounded-md">
          <div className="p-2 space-y-1">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading devices...
              </div>
            ) : filteredDevices.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No devices found
              </div>
            ) : (
              filteredDevices.map((device) => {
                const isSelected = selectedIds.has(device.device_id);
                const isDisabled =
                  !isSelected && selectedIds.size >= newDeviceLimit;

                return (
                  <div
                    key={device.device_id}
                    className={`flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-green-50 border border-green-200"
                        : isDisabled
                        ? "opacity-50 cursor-not-allowed"
                        : "hover:bg-muted"
                    }`}
                    onClick={() => !isDisabled && toggleDevice(device.device_id)}
                  >
                    <Checkbox
                      checked={isSelected}
                      disabled={isDisabled}
                      className={isSelected ? "border-green-600" : ""}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-sm truncate">
                        {device.device_id}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Site: {device.site_id}
                        {device.tags && device.tags.length > 0 && (
                          <span className="ml-2">
                            Tags: {device.tags.slice(0, 3).join(", ")}
                          </span>
                        )}
                      </div>
                    </div>
                    {isSelected && (
                      <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>

        <DialogFooter className="pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!isExactCount}
            className={isExactCount ? "bg-green-600 hover:bg-green-700" : ""}
          >
            {isExactCount
              ? "Confirm Selection"
              : `Select ${newDeviceLimit - selectedIds.size} more`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## Usage Example

```tsx
import { useState } from "react";
import { DeviceSelectionModal } from "@/features/subscription/DeviceSelectionModal";

function SubscriptionDowngradeFlow() {
  const [showModal, setShowModal] = useState(false);

  const handleDeviceSelection = async (selectedDeviceIds: string[]) => {
    // Call API to update subscription and deactivate non-selected devices
    await apiPost("/customer/subscription/downgrade", {
      keep_device_ids: selectedDeviceIds,
    });
  };

  return (
    <>
      <Button onClick={() => setShowModal(true)}>
        Change to 30-device plan
      </Button>

      <DeviceSelectionModal
        open={showModal}
        onOpenChange={setShowModal}
        currentDeviceCount={50}
        newDeviceLimit={30}
        onConfirm={handleDeviceSelection}
      />
    </>
  );
}
```

## Backend Endpoint (for reference)

The modal will need a backend endpoint to handle the downgrade:

```python
@router.post("/subscription/downgrade")
async def downgrade_subscription(data: DowngradeRequest):
    """
    Downgrade subscription and deactivate non-selected devices.

    Request body:
    {
      "keep_device_ids": ["device-1", "device-2", ...]
    }
    """
    # Validate that keep_device_ids count matches new limit
    # Mark non-selected devices as INACTIVE
    # Update subscription device count
    pass
```

## Testing

1. Open modal with currentDeviceCount=50, newDeviceLimit=30
2. Verify you can only select up to 30 devices
3. Verify confirm button is disabled until exactly 30 selected
4. Test search filtering
5. Test "Select First N" button
6. Verify selected devices are highlighted in green
7. Verify warning shows correct count of devices to be deactivated

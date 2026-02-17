import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Search, AlertTriangle } from "lucide-react";
import { apiGet } from "@/services/api/client";

interface Device {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscriptionId: string;
  requiredCount: number;
  selectedDevices: string[];
  onSelectionChange: (devices: string[]) => void;
}

export function DeviceSelectionModal({
  open,
  onOpenChange,
  subscriptionId,
  requiredCount,
  selectedDevices,
  onSelectionChange,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("");

  const { data } = useQuery({
    queryKey: ["subscription-devices", subscriptionId],
    queryFn: () =>
      apiGet<{ devices: Device[] }>(`/customer/subscriptions/${subscriptionId}`),
    enabled: open,
  });

  const devices = data?.devices || [];

  const filteredDevices = useMemo(() => {
    if (!searchQuery) return devices;
    const q = searchQuery.toLowerCase();
    return devices.filter(
      (device) =>
        device.device_id.toLowerCase().includes(q) ||
        device.site_id.toLowerCase().includes(q)
    );
  }, [devices, searchQuery]);

  const toggleDevice = (deviceId: string) => {
    if (selectedDevices.includes(deviceId)) {
      onSelectionChange(selectedDevices.filter((id) => id !== deviceId));
    } else if (selectedDevices.length < requiredCount) {
      onSelectionChange([...selectedDevices, deviceId]);
    }
  };

  const isComplete = selectedDevices.length === requiredCount;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-lg flex-col">
        <DialogHeader>
          <DialogTitle>Select Devices to Deactivate</DialogTitle>
          <DialogDescription>
            Choose {requiredCount} device(s) that will be deactivated when you
            renew with the smaller plan. These devices will stop sending
            telemetry.
          </DialogDescription>
        </DialogHeader>

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
          <Badge variant={isComplete ? "default" : "outline"}>
            {selectedDevices.length} / {requiredCount}
          </Badge>
        </div>

        <ScrollArea className="flex-1 rounded-md border">
          <div className="space-y-1 p-2">
            {filteredDevices.map((device) => {
              const isSelected = selectedDevices.includes(device.device_id);
              const isDisabled =
                !isSelected && selectedDevices.length >= requiredCount;
              return (
                <div
                  key={device.device_id}
                  className={`flex cursor-pointer items-center gap-3 rounded p-2 ${
                    isSelected
                      ? "border border-destructive/20 bg-destructive/10"
                      : isDisabled
                      ? "opacity-50"
                      : "hover:bg-muted"
                  }`}
                  onClick={() => !isDisabled && toggleDevice(device.device_id)}
                >
                  <Checkbox checked={isSelected} disabled={isDisabled} />
                  <div className="flex-1">
                    <div className="font-mono text-sm">{device.device_id}</div>
                    <div className="text-sm text-muted-foreground">
                      Site: {device.site_id}
                    </div>
                  </div>
                  <Badge variant="outline">
                    {device.status}
                  </Badge>
                </div>
              );
            })}
          </div>
        </ScrollArea>

        {isComplete && (
          <div className="rounded-md bg-orange-50 p-3 text-sm dark:bg-orange-950">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-orange-600" />
              <div>
                <p className="font-medium text-orange-800 dark:text-orange-200">
                  {selectedDevices.length} device(s) will be deactivated
                </p>
                <p className="mt-1 text-sm text-orange-700 dark:text-orange-300">
                  These devices will stop accepting telemetry after renewal.
                </p>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => onOpenChange(false)} disabled={!isComplete}>
            Confirm Selection
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

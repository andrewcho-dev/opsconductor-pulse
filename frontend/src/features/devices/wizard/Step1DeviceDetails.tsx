import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchSites } from "@/services/api/sites";
import type { DeviceDetailsData } from "./types";

interface Step1DeviceDetailsProps {
  onNext: (data: DeviceDetailsData) => void;
  initialData?: DeviceDetailsData | null;
}

const DEVICE_TYPES = [
  "temperature",
  "humidity",
  "pressure",
  "vibration",
  "power",
  "flow",
  "level",
  "gateway",
];

export function Step1DeviceDetails({ onNext, initialData }: Step1DeviceDetailsProps) {
  const [name, setName] = useState(initialData?.name ?? "");
  const [deviceType, setDeviceType] = useState(initialData?.device_type ?? "");
  const [siteId, setSiteId] = useState(initialData?.site_id ?? "");
  const { data } = useQuery({
    queryKey: ["sites"],
    queryFn: fetchSites,
  });
  const sites = useMemo(() => data?.sites ?? [], [data?.sites]);

  return (
    <div className="space-y-4">
      <div className="grid gap-2">
        <Label htmlFor="wizard-device-name">Device Name</Label>
        <Input
          id="wizard-device-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Field Sensor A"
        />
      </div>
      <div className="grid gap-2">
        <Label>Device Type</Label>
        <select
          className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={deviceType}
          onChange={(event) => setDeviceType(event.target.value)}
        >
          <option value="">Select device type</option>
          {DEVICE_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-2">
        <Label>Site</Label>
        <select
          className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={siteId}
          onChange={(event) => setSiteId(event.target.value)}
        >
          <option value="">Default site</option>
          {sites.map((site) => (
            <option key={site.site_id} value={site.site_id}>
              {site.name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex justify-end">
        <Button
          disabled={!name.trim() || !deviceType}
          onClick={() =>
            onNext({
              name: name.trim(),
              device_type: deviceType,
              site_id: siteId || undefined,
            })
          }
        >
          Next
        </Button>
      </div>
    </div>
  );
}

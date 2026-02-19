import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchSites } from "@/services/api/sites";
import { listTemplates } from "@/services/api/templates";
import type { DeviceDetailsData } from "./types";

interface Step1DeviceDetailsProps {
  onNext: (data: DeviceDetailsData) => void;
  initialData?: DeviceDetailsData | null;
}

export function Step1DeviceDetails({ onNext, initialData }: Step1DeviceDetailsProps) {
  const [name, setName] = useState(initialData?.name ?? "");
  const [deviceType, setDeviceType] = useState(initialData?.device_type ?? "");
  const [templateId, setTemplateId] = useState<string>(
    initialData?.template_id != null ? String(initialData.template_id) : ""
  );
  const [siteId, setSiteId] = useState(initialData?.site_id ?? "");
  const { data } = useQuery({
    queryKey: ["sites"],
    queryFn: fetchSites,
  });
  const { data: templates } = useQuery({
    queryKey: ["templates", "wizard-step1"],
    queryFn: () => listTemplates(),
  });
  const sites = useMemo(() => data?.sites ?? [], [data?.sites]);
  const templateOptions = useMemo(() => templates ?? [], [templates]);

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
        <Label>Template (recommended)</Label>
        <select
          className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={templateId}
          onChange={(event) => setTemplateId(event.target.value)}
        >
          <option value="">None</option>
          {templateOptions
            .slice()
            .sort((a, b) => (a.source === b.source ? a.name.localeCompare(b.name) : a.source === "system" ? -1 : 1))
            .map((t) => (
              <option key={t.id} value={String(t.id)}>
                {t.name} ({t.category}){t.source === "system" ? " [system]" : ""}
              </option>
            ))}
        </select>
        <div className="text-xs text-muted-foreground">
          Device type is still supported, but templates unlock modules, transports, and semantic telemetry.
        </div>
      </div>
      <div className="grid gap-2">
        <Label>Device Type</Label>
        <Input
          value={deviceType}
          onChange={(event) => setDeviceType(event.target.value)}
          placeholder="gateway"
        />
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
              template_id: templateId ? Number(templateId) : undefined,
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

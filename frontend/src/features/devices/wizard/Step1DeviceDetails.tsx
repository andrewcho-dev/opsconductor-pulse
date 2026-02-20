import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchSites } from "@/services/api/sites";
import { listTemplates } from "@/services/api/templates";
import type { DeviceDetailsData } from "./types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

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
        <Select
          value={templateId || "none"}
          onValueChange={(v) => setTemplateId(v === "none" ? "" : v)}
        >
          <SelectTrigger className="h-10 w-full">
            <SelectValue placeholder="None" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            {templateOptions
              .slice()
              .sort((a, b) =>
                a.source === b.source ? a.name.localeCompare(b.name) : a.source === "system" ? -1 : 1
              )
              .map((t) => (
                <SelectItem key={t.id} value={String(t.id)}>
                  {t.name} ({t.category}){t.source === "system" ? " [system]" : ""}
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
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
        <Select value={siteId || "default"} onValueChange={(v) => setSiteId(v === "default" ? "" : v)}>
          <SelectTrigger className="h-10 w-full">
            <SelectValue placeholder="Default site" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="default">Default site</SelectItem>
            {sites.map((site) => (
              <SelectItem key={site.site_id} value={site.site_id}>
                {site.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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

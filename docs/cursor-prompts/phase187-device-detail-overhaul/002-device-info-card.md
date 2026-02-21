# Task 2: Rewrite DeviceInfoCard as a Properties Panel

## File

`frontend/src/features/devices/DeviceInfoCard.tsx`

## Current Problems

1. Everything crammed into one card with `p-2` padding — 16+ fields with no grouping
2. `grid grid-cols-4` of `text-sm` key-value pairs — unreadable wall of tiny text
3. Tags are inline with a tiny `w-12` input field and a "+" placeholder
4. Notes are a borderless inline input with no label
5. Location is a run-on line of text with brackets like `[manual]`
6. No visual sections — Model, MAC, IMEI, Tags all at the same level

## Goal

Rewrite as a properly organized properties panel with labeled sections, matching how AWS IoT and ThingsBoard present device properties.

## Complete Rewrite

Replace the entire file content:

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Pencil, Plus, X } from "lucide-react";
import { StatusBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import type { Device } from "@/services/api/types";
import { formatTimestamp } from "@/lib/format";

interface DeviceInfoCardProps {
  device: Device | undefined;
  isLoading: boolean;
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  notesValue: string;
  onNotesChange: (value: string) => void;
  onNotesBlur?: () => void;
  onEdit: () => void;
}

function PropertyRow({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-4 py-1.5">
      <span className="text-sm text-muted-foreground whitespace-nowrap">{label}</span>
      <span className={`text-sm text-right ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );
}

export function DeviceInfoCard({
  device,
  isLoading,
  tags,
  onTagsChange,
  notesValue,
  onNotesChange,
  onNotesBlur,
  onEdit,
}: DeviceInfoCardProps) {
  const [tagInput, setTagInput] = useState("");

  if (isLoading) {
    return (
      <div className="rounded-md border border-border p-4 space-y-3">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-4 w-56" />
        <Skeleton className="h-4 w-40" />
      </div>
    );
  }

  if (!device) {
    return (
      <div className="rounded-md border border-border p-4">
        <p className="text-sm text-muted-foreground">Device not found.</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border divide-y divide-border">
      {/* Section: Identity */}
      <div className="p-4 space-y-1">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Identity</h4>
          <Button
            type="button"
            onClick={onEdit}
            variant="ghost"
            size="sm"
            className="h-7 text-muted-foreground hover:text-foreground"
          >
            <Pencil className="mr-1 h-3 w-3" />
            Edit
          </Button>
        </div>
        <div className="flex items-center justify-between gap-4 py-1.5">
          <span className="text-sm text-muted-foreground">Device ID</span>
          <div className="flex items-center gap-1.5">
            <code className="text-sm font-mono">{device.device_id}</code>
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-6 w-6"
              onClick={() => {
                void navigator.clipboard.writeText(device.device_id);
                toast.success("Copied to clipboard");
              }}
            >
              <Copy className="h-3 w-3" />
            </Button>
          </div>
        </div>
        <PropertyRow label="Site" value={device.site_id} />
        {device.template && (
          <div className="flex items-center justify-between gap-4 py-1.5">
            <span className="text-sm text-muted-foreground">Template</span>
            <Link
              to={`/templates/${device.template.id}`}
              className="text-sm text-primary hover:underline"
            >
              {device.template.name}
            </Link>
          </div>
        )}
        <PropertyRow label="Last Seen" value={formatTimestamp(device.last_seen_at)} />
      </div>

      {/* Section: Hardware */}
      {(device.model || device.manufacturer || device.serial_number || device.mac_address || device.hw_revision || device.fw_version) && (
        <div className="p-4 space-y-1">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Hardware</h4>
          <PropertyRow label="Model" value={device.model} />
          <PropertyRow label="Manufacturer" value={device.manufacturer} />
          <PropertyRow label="Serial Number" value={device.serial_number} mono />
          <PropertyRow label="MAC Address" value={device.mac_address} mono />
          <PropertyRow label="HW Revision" value={device.hw_revision} />
          <PropertyRow label="FW Version" value={device.fw_version} mono />
        </div>
      )}

      {/* Section: Network */}
      {(device.imei || device.iccid) && (
        <div className="p-4 space-y-1">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Network</h4>
          <PropertyRow label="IMEI" value={device.imei} mono />
          <PropertyRow label="SIM / ICCID" value={device.iccid} mono />
        </div>
      )}

      {/* Section: Location */}
      {(device.latitude != null || device.address) && (
        <div className="p-4 space-y-1">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Location</h4>
          {device.latitude != null && device.longitude != null && (
            <PropertyRow
              label="Coordinates"
              value={`${device.latitude.toFixed(6)}, ${device.longitude.toFixed(6)}`}
              mono
            />
          )}
          <PropertyRow label="Address" value={device.address} />
          <PropertyRow label="Source" value={device.location_source ?? "auto"} />
        </div>
      )}

      {/* Section: Tags */}
      <div className="p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Tags</h4>
        <div className="flex flex-wrap items-center gap-1.5">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 pr-1">
              {tag}
              <Button
                type="button"
                onClick={() => onTagsChange(tags.filter((t) => t !== tag))}
                variant="ghost"
                size="icon-sm"
                className="h-4 w-4 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
          <div className="flex items-center gap-1">
            <Input
              type="text"
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              className="h-7 w-28 text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const next = tagInput.trim();
                  if (!next) return;
                  if (tags.some((t) => t.toLowerCase() === next.toLowerCase())) {
                    setTagInput("");
                    return;
                  }
                  onTagsChange([...tags, next]);
                  setTagInput("");
                } else if (e.key === "Backspace" && !tagInput && tags.length > 0) {
                  onTagsChange(tags.slice(0, -1));
                }
              }}
            />
          </div>
          {tags.length === 0 && !tagInput && (
            <span className="text-sm text-muted-foreground">No tags</span>
          )}
        </div>
      </div>

      {/* Section: Notes */}
      <div className="p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Notes</h4>
        <Textarea
          value={notesValue}
          onChange={(e) => onNotesChange(e.target.value)}
          onBlur={onNotesBlur}
          placeholder="Add notes about this device..."
          rows={2}
          className="text-sm"
        />
      </div>
    </div>
  );
}
```

## Key Design Decisions

1. **Sections with dividers** — `divide-y divide-border` creates clean visual separation between Identity, Hardware, Network, Location, Tags, Notes
2. **Section headers** — Uppercase muted labels like "IDENTITY", "HARDWARE", matching the fieldset pattern from Phase 184
3. **Conditional sections** — Hardware, Network, and Location sections only render if device has those fields populated. No "—" walls.
4. **PropertyRow component** — Consistent label-value layout with optional monospace for technical identifiers
5. **Tags use Badge** — Proper Badge components instead of raw spans
6. **Notes use Textarea** — Proper labeled textarea instead of a borderless inline input
7. **Copy button** — Device ID has a copy-to-clipboard button with toast feedback
8. **Template link** — Clickable link to template detail page
9. **Edit button** — Moved to the Identity section header (contextually appropriate)

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Device properties organized in labeled sections: Identity, Hardware, Network, Location, Tags, Notes
- Empty sections (no hardware info) don't render at all
- Tags use proper Badge components with X remove buttons
- Notes is a labeled Textarea
- Device ID has copy button
- Template name is a clickable link
- Edit button in Identity section header

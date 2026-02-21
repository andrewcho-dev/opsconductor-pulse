# Task 1: Fix Overview Tab Layout

## Files

1. `frontend/src/features/devices/DeviceInfoCard.tsx` — Replace with compact property cards
2. `frontend/src/features/devices/DeviceDetailPage.tsx` — Fix the Overview tab grid

## Problem

The current layout has:
- `lg:grid-cols-[1fr_360px]` — gives properties ~900px, telemetry 360px
- DeviceInfoCard is one tall vertical column with `divide-y` sections stacked
- PropertyRow uses `justify-between` which spreads labels and values to opposite edges across the full ~900px width — massive dead whitespace

## Fix Part A: Rewrite DeviceInfoCard.tsx

Replace DeviceInfoCard with a component that returns MULTIPLE cards instead of one monolithic card. The parent will arrange them in a grid.

**Replace the entire `DeviceInfoCard.tsx` with:**

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Pencil, X } from "lucide-react";
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

function Prop({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2 py-1 text-sm">
      <span className="w-20 shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate">{children}</span>
    </div>
  );
}

function PropMono({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-2 py-1 text-sm">
      <span className="w-20 shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate font-mono">{value}</span>
    </div>
  );
}

function SectionCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h4>
        {action}
      </div>
      {children}
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
      <div className="col-span-full grid gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((n) => (
          <div key={n} className="rounded-md border border-border p-3 space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-28" />
          </div>
        ))}
      </div>
    );
  }

  if (!device) {
    return (
      <div className="col-span-full rounded-md border border-border p-4">
        <p className="text-sm text-muted-foreground">Device not found.</p>
      </div>
    );
  }

  const hasHardware =
    device.model || device.manufacturer || device.serial_number ||
    device.mac_address || device.hw_revision || device.fw_version;
  const hasNetwork = device.imei || device.iccid;
  const hasLocation = device.latitude != null || device.address;

  return (
    <>
      {/* Row 1: Identity + Hardware + Network/Location in a 3-col grid */}
      <div className="col-span-full grid gap-3 sm:grid-cols-3">
        {/* Identity */}
        <SectionCard
          title="Identity"
          action={
            <Button
              type="button"
              onClick={onEdit}
              variant="ghost"
              size="sm"
              className="h-6 text-xs text-muted-foreground hover:text-foreground"
            >
              <Pencil className="mr-1 h-3 w-3" />
              Edit
            </Button>
          }
        >
          <div className="flex gap-2 py-1 text-sm">
            <span className="w-20 shrink-0 text-muted-foreground">Device ID</span>
            <code className="min-w-0 truncate font-mono">{device.device_id}</code>
            <Button
              variant="ghost"
              size="icon-sm"
              className="ml-auto h-5 w-5 shrink-0"
              onClick={() => {
                void navigator.clipboard.writeText(device.device_id);
                toast.success("Copied");
              }}
            >
              <Copy className="h-3 w-3" />
            </Button>
          </div>
          <Prop label="Site">{device.site_id || "—"}</Prop>
          {device.template ? (
            <div className="flex gap-2 py-1 text-sm">
              <span className="w-20 shrink-0 text-muted-foreground">Template</span>
              <Link
                to={`/templates/${device.template.id}`}
                className="min-w-0 truncate text-primary hover:underline"
              >
                {device.template.name}
              </Link>
            </div>
          ) : null}
          <Prop label="Last Seen">{formatTimestamp(device.last_seen_at) || "never"}</Prop>
        </SectionCard>

        {/* Hardware */}
        {hasHardware ? (
          <SectionCard title="Hardware">
            <Prop label="Model">{device.model || "—"}</Prop>
            <Prop label="Mfr">{device.manufacturer || "—"}</Prop>
            <PropMono label="Serial" value={device.serial_number} />
            <PropMono label="MAC" value={device.mac_address} />
            <Prop label="HW Rev">{device.hw_revision || "—"}</Prop>
            <PropMono label="FW Ver" value={device.fw_version} />
          </SectionCard>
        ) : (
          <div />
        )}

        {/* Network + Location stacked in the 3rd column */}
        <div className="space-y-3">
          {hasNetwork && (
            <SectionCard title="Network">
              <PropMono label="IMEI" value={device.imei} />
              <PropMono label="SIM" value={device.iccid} />
            </SectionCard>
          )}
          {hasLocation && (
            <SectionCard title="Location">
              {device.latitude != null && device.longitude != null && (
                <PropMono
                  label="Coords"
                  value={`${device.latitude.toFixed(4)}, ${device.longitude.toFixed(4)}`}
                />
              )}
              {device.address && <Prop label="Address">{device.address}</Prop>}
            </SectionCard>
          )}
        </div>
      </div>

      {/* Row 2: Tags + Notes side by side */}
      <div className="col-span-full grid gap-3 sm:grid-cols-2">
        <SectionCard title="Tags">
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
            <Input
              type="text"
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              className="h-7 w-24 text-sm"
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
            {tags.length === 0 && !tagInput && (
              <span className="text-sm text-muted-foreground">No tags</span>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Notes">
          <Textarea
            value={notesValue}
            onChange={(e) => onNotesChange(e.target.value)}
            onBlur={onNotesBlur}
            placeholder="Add notes about this device..."
            rows={2}
            className="text-sm"
          />
        </SectionCard>
      </div>
    </>
  );
}
```

### Key design changes:

1. **`Prop` component uses fixed `w-20` label** — labels are a consistent 80px wide, values immediately follow. No more `justify-between` stretching across 900px.
2. **`SectionCard` is a reusable bordered card** — each section is its own compact card.
3. **The component returns `<>` fragments** — NOT a single card. The parent grid arranges the cards.
4. **3-column grid for properties** — Identity | Hardware | Network+Location stacked.
5. **Tags + Notes side-by-side** in a 2-column grid below.
6. **`truncate` on values** — long serial numbers and IDs truncate instead of wrapping.

## Fix Part B: Update DeviceDetailPage.tsx Overview tab

Replace the Overview tab's TabsContent (the `lg:grid-cols-[1fr_360px]` section) with a simpler layout where DeviceInfoCard's fragments flow naturally:

```tsx
<TabsContent value="overview" className="pt-2 space-y-4">
  {/* DeviceInfoCard now returns fragment with its own grid rows */}
  <DeviceInfoCard
    device={device}
    isLoading={deviceLoading}
    tags={deviceTags}
    onTagsChange={(next) => {
      setDeviceTagsState(next);
      void handleSaveTags(next);
    }}
    notesValue={notesValue}
    onNotesChange={handleNotesChange}
    onNotesBlur={handleSaveNotes}
    onEdit={() => setEditModalOpen(true)}
  />

  {/* Latest Telemetry — full width */}
  <div className="rounded-md border border-border p-4">
    <h4 className="mb-3 text-sm font-semibold">Latest Telemetry</h4>
    {latestMetrics.length === 0 ? (
      <p className="text-sm text-muted-foreground">No telemetry data yet.</p>
    ) : (
      <div className="grid gap-x-6 gap-y-1 sm:grid-cols-2 md:grid-cols-4">
        {latestMetrics.map(([name, value]) => (
          <div key={name} className="flex items-center justify-between py-1 text-sm">
            <span className="text-muted-foreground">{name}</span>
            <span className="font-mono font-medium">{String(value)}</span>
          </div>
        ))}
      </div>
    )}
    {latestMetrics.length > 0 && (
      <div className="mt-2 text-right text-xs text-muted-foreground">
        Updated {relativeTime(points.at(-1)?.timestamp)}
      </div>
    )}
  </div>

  {/* Map — full width, only if coordinates exist */}
  {device?.latitude != null && device?.longitude != null && (
    <div className="relative h-[200px]">
      <DeviceMapCard
        latitude={pendingLocation?.lat ?? device.latitude}
        longitude={pendingLocation?.lng ?? device.longitude}
        address={device.address}
        editable
        onLocationChange={handleMapLocationChange}
      />
      {pendingLocation && (
        <div className="absolute bottom-2 right-2 z-[1000] flex gap-1">
          <Button size="sm" className="h-8" onClick={handleSaveLocation}>
            Save Location
          </Button>
          <Button size="sm" variant="outline" className="h-8" onClick={() => setPendingLocation(null)}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  )}

  {/* Plan panel */}
  {deviceId && <DevicePlanPanel deviceId={deviceId} />}
</TabsContent>
```

### Key changes from Phase 187:
- **Removed `lg:grid-cols-[1fr_360px]` wrapper** — no more 2-column split
- **DeviceInfoCard sits at top** — its internal 3-col grid handles property layout
- **Telemetry is full-width below properties** — uses a 4-column grid for metrics so they're compact and horizontal
- **Map is full-width with fixed 200px height** — only when coordinates exist
- **Plan panel at bottom** — same as before

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Property sections (Identity, Hardware, Network/Location) arranged in 3-column grid
- Labels are fixed-width (80px), values immediately adjacent — no stretching
- Telemetry metrics in 4-column horizontal grid, full width
- Tags + Notes side by side
- Map only shows when coordinates exist, 200px height
- Page fits on screen without excessive scrolling
- All edit/tag/note/map functionality still works

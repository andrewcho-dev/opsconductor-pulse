# Task 1: Create DeviceHealthStrip + Slim Overview Tab

## New File

**Create:** `frontend/src/features/devices/DeviceHealthStrip.tsx`

```tsx
import { useQuery } from "@tanstack/react-query";
import { Cpu, Gauge, HardDrive, Signal, Timer } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { getDeviceHealth } from "@/services/api/sensors";

interface DeviceHealthStripProps {
  deviceId: string;
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function humanizeUptime(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "\u2014";
  const s = Math.floor(seconds);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function signalColorClass(signalQuality: number | null): string {
  if (signalQuality == null || !Number.isFinite(signalQuality)) return "text-foreground";
  if (signalQuality >= 60) return "text-status-online";
  if (signalQuality >= 30) return "text-status-warning";
  return "text-status-critical";
}

function cpuTempColorClass(cpuTempC: number | null): string {
  if (cpuTempC == null || !Number.isFinite(cpuTempC)) return "text-foreground";
  if (cpuTempC < 60) return "text-status-online";
  if (cpuTempC < 80) return "text-status-warning";
  return "text-status-critical";
}

export function DeviceHealthStrip({ deviceId }: DeviceHealthStripProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["device-health", deviceId, "24h"],
    queryFn: () => getDeviceHealth(deviceId, "24h", 1),
    enabled: !!deviceId,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const latest = data?.latest ?? null;

  if (isLoading) {
    return (
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (!latest) return null;

  return (
    <div className="grid grid-cols-5 gap-2">
      <MiniStat
        icon={<Signal className="h-4 w-4 text-muted-foreground" />}
        label="Signal"
        value={
          latest.signal_quality != null ? (
            <span className={signalColorClass(latest.signal_quality)}>
              {clamp(latest.signal_quality, 0, 100)}%
            </span>
          ) : (
            "\u2014"
          )
        }
        subValue={latest.rssi != null ? `${latest.rssi} dBm` : "\u2014"}
      />
      <MiniStat
        icon={<Gauge className="h-4 w-4 text-muted-foreground" />}
        label="Battery"
        value={
          latest.battery_pct != null ? (
            `${clamp(latest.battery_pct, 0, 100)}%`
          ) : latest.power_source === "line" ? (
            "Line"
          ) : latest.power_source === "poe" ? (
            "PoE"
          ) : (
            "N/A"
          )
        }
        subValue={
          latest.battery_voltage != null
            ? `${latest.battery_voltage.toFixed(2)} V`
            : latest.power_source
              ? `(${latest.power_source})`
              : "\u2014"
        }
      />
      <MiniStat
        icon={<Cpu className="h-4 w-4 text-muted-foreground" />}
        label="CPU Temp"
        value={
          latest.cpu_temp_c != null ? (
            <span className={cpuTempColorClass(latest.cpu_temp_c)}>
              {latest.cpu_temp_c.toFixed(1)}&deg;C
            </span>
          ) : (
            "\u2014"
          )
        }
        subValue=" "
      />
      <MiniStat
        icon={<HardDrive className="h-4 w-4 text-muted-foreground" />}
        label="Memory"
        value={latest.memory_used_pct != null ? `${clamp(latest.memory_used_pct, 0, 100)}%` : "\u2014"}
        subValue={
          latest.storage_used_pct != null ? `Storage ${clamp(latest.storage_used_pct, 0, 100)}%` : "\u2014"
        }
      />
      <MiniStat
        icon={<Timer className="h-4 w-4 text-muted-foreground" />}
        label="Uptime"
        value={humanizeUptime(latest.uptime_seconds)}
        subValue={latest.reboot_count != null ? `${latest.reboot_count} reboots` : "\u2014"}
      />
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
  subValue,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  subValue: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border p-2 space-y-1">
      <div className="flex items-center gap-2">
        {icon}
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
      <div className="text-lg font-semibold leading-none">{value}</div>
      <div className="text-xs text-muted-foreground truncate">{subValue}</div>
    </div>
  );
}
```

---

## Modify: `frontend/src/features/devices/DeviceDetailPage.tsx`

### Step 1: Update imports

**Remove** these two imports:
```tsx
import { DeviceHealthPanel } from "./DeviceHealthPanel";
import { DeviceUptimePanel } from "./DeviceUptimePanel";
```

**Add** this import:
```tsx
import { DeviceHealthStrip } from "./DeviceHealthStrip";
```

### Step 2: Remove `latestMetrics` computation

**Delete** the entire `latestMetrics` useMemo block (approximately lines 104-108):
```tsx
  const latestMetrics = useMemo(() => {
    const latest = points.at(-1);
    if (!latest) return [];
    return Object.entries(latest.metrics).slice(0, 12);
  }, [points]);
```

Also remove `useMemo` from the react import if it's no longer used by anything else in the file. (Check — if nothing else uses `useMemo`, remove it from the import.)

### Step 3: Replace Overview tab content

Replace the entire `<TabsContent value="overview">` block with:

```tsx
        <TabsContent value="overview" className="pt-2 space-y-4">
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

          {deviceId && <DeviceHealthStrip deviceId={deviceId} />}

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
        </TabsContent>
```

### What was removed from Overview:

1. `DeviceHealthPanel` — replaced by `DeviceHealthStrip` (compact 5-metric row, no chart, no time range selector, no health details row)
2. "Latest Telemetry" card (the bordered card with 4-column metric grid and "Updated X ago") — removed entirely (telemetry is on the Data tab)
3. `DeviceUptimePanel` — removed entirely (uptime value is already in the health strip's Uptime stat box)

### What was kept:

1. `DeviceInfoCard` — identity property cards (unchanged)
2. `DeviceHealthStrip` — compact 5 stat boxes: Signal, Battery, CPU Temp, Memory, Uptime
3. `DeviceMapCard` — location pin (unchanged)
4. `useDeviceTelemetry` hook — still called (passed to Data tab's `DeviceSensorsDataTab`)

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Overview tab shows only: property cards, 5-stat health strip, map
- No charts anywhere on Overview
- No "Latest Telemetry" grid
- No uptime bar or time range selectors
- Data tab still works (telemetry charts, sensors, modules)
- Manage tab unchanged
- Health strip shows colored values (green/yellow/red for signal and CPU temp)
- When no health data exists, health strip renders nothing (no "No data" message cluttering the page)

# Phase 148e — Fleet Overview Widget Overhaul

## Problem

The `fleet_overview` widget forces the user to pick ONE of three mutually exclusive display modes (count, donut, health), each showing a tiny slice of available data. A widget called "Fleet Overview" should actually overview the fleet — combining all key metrics into a single composite view.

## Data Already Available (no backend changes needed)

Three existing API calls return everything we need:

1. **`fetchFleetSummary()`** → `FleetSummary`
   - `ONLINE`, `STALE`, `OFFLINE`, `total`
   - `alerts_open`, `alerts_new_1h` (optional)
   - `low_battery_count` (optional)

2. **`fetchFleetHealth()`** → `FleetHealthResponse`
   - `score` (0-100), `total_devices`, `online`, `critical_alerts`

3. **`getFleetUptimeSummary()`** → `FleetUptimeSummary`
   - `avg_uptime_pct`, `total_devices`, `online`, `offline`

All three are already imported/importable from `frontend/src/services/api/devices.ts`.

## Design — Composite Fleet Overview

Replace the three mutually exclusive modes with a single composite layout that shows everything at a glance. Remove the `display_mode` config option entirely — this widget now always shows the full overview.

### Layout (target default size: 6×3, 600px × 300px)

```
┌─────────────────────────────────────────────────────────┐
│  HEALTH SCORE        STATUS BREAKDOWN        UPTIME     │
│  ┌─────────┐     Online   ██████ 142        ┌───────┐  │
│  │  87%    │     Stale    ███     12        │ 99.2% │  │
│  │  (gauge) │     Offline  ██      8        │uptime │  │
│  └─────────┘                                └───────┘  │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  🔔 3 open alerts   ⚡ 1 new (1h)   🔋 2 low battery   │
│  ⚠️ 1 critical                                          │
└─────────────────────────────────────────────────────────┘
```

### Top Row — Three Sections Side by Side

**Left: Health Score** (reuse the SVG circular gauge from current HealthView)
- Circular progress ring showing `score` from `fetchFleetHealth()`
- Score percentage in center
- Color based on thresholds (configurable)
- Label "Health" below

**Center: Device Status Breakdown**
- Three rows: Online / Stale / Offline
- Each row: colored dot + label + horizontal bar (proportional to total) + count
- Bar colors: green (online), orange (stale), red (offline)
- Total device count shown as "{total} devices" subheading

**Right: Uptime**
- Large `avg_uptime_pct` from `getFleetUptimeSummary()` (e.g., "99.2%")
- Label "Avg Uptime" below
- Color: green if ≥99%, orange if ≥95%, red if <95%

### Bottom Row — Alert & Battery Summary Strip

A compact horizontal strip with icon + count pairs:
- Open alerts: `alerts_open` from fleet summary (bell icon)
- New alerts (1h): `alerts_new_1h` (bolt/zap icon)
- Critical alerts: `critical_alerts` from fleet health (alert-triangle icon)
- Low battery: `low_battery_count` from fleet summary (battery icon)

Only show items that have a non-zero count. If all are zero, show "All clear" in green.

Use Lucide icons already in the project: `Bell`, `Zap`, `AlertTriangle`, `Battery`.

### Responsive Behavior

At smaller sizes (w < 4), stack vertically:
- Health gauge + uptime on top row
- Status bars below
- Alert strip at bottom

## Files to Modify

### 1. `frontend/src/features/dashboard/widgets/renderers/FleetOverviewRenderer.tsx`

**Complete rewrite.** Replace the three separate view components (`CountView`, `DonutView`, `HealthView`) with a single composite `FleetOverviewRenderer`.

Key changes:
- Fetch all three data sources in parallel using three `useQuery` hooks
- Remove `DisplayMode` type and `display_mode` switch logic
- Build the composite layout described above
- Keep the SVG circular gauge from HealthView (it's clean and lightweight — no ECharts needed for it)
- Use simple Tailwind-styled horizontal bars for status breakdown (no ECharts — keep it fast)
- Import `getFleetUptimeSummary` from `@/services/api/devices`
- Import Lucide icons: `Bell`, `Zap`, `AlertTriangle`, `Battery` from `lucide-react`
- All three queries use `refetchInterval: 30_000`

Structure:
```tsx
export default function FleetOverviewRenderer({ config }: WidgetRendererProps) {
  // Three parallel queries
  const { data: summary, isLoading: l1 } = useQuery({ queryKey: ["fleet-summary"], queryFn: fetchFleetSummary, refetchInterval: 30_000 });
  const { data: health, isLoading: l2 } = useQuery({ queryKey: ["fleet-health"], queryFn: fetchFleetHealth, refetchInterval: 30_000 });
  const { data: uptime, isLoading: l3 } = useQuery({ queryKey: ["fleet-uptime-summary"], queryFn: getFleetUptimeSummary, refetchInterval: 30_000 });

  if (l1 || l2 || l3) return <Skeleton ... />;

  return (
    <div className="h-full flex flex-col gap-2 px-2 py-1">
      {/* Top row: health gauge | status bars | uptime */}
      <div className="flex-1 flex items-center gap-4 min-h-0">
        <HealthGauge score={health.score} thresholds={config.thresholds} />
        <StatusBars online={...} stale={...} offline={...} total={...} />
        <UptimeDisplay pct={uptime.avg_uptime_pct} />
      </div>
      {/* Bottom strip: alerts & battery */}
      <AlertStrip
        alertsOpen={summary.alerts_open}
        alertsNew={summary.alerts_new_1h}
        critical={health.critical_alerts}
        lowBattery={summary.low_battery_count}
      />
    </div>
  );
}
```

### 2. `frontend/src/features/dashboard/widgets/widget-registry.ts`

Update the `fleet_overview` entry:
- Change `defaultSize` from `{ w: 3, h: 2 }` to `{ w: 6, h: 3 }`
- Change `minSize` from `{ w: 2, h: 1 }` to `{ w: 4, h: 2 }`
- Change `defaultConfig` from `{ display_mode: "count" }` to `{}` (no display_mode needed)
- Update `description` to: `"Composite fleet dashboard — health score, device status, uptime, alerts, and battery at a glance."`

### 3. `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

Remove any `fleet_overview`-specific config sections that reference `display_mode` selection. The widget no longer has display modes. Keep threshold config if it exists (thresholds still apply to the health gauge color).

## What NOT to Change

- No backend changes
- No new API endpoints
- No new dependencies
- Don't touch other widget renderers

## Verification

1. Add a fleet_overview widget to a dashboard
2. It should render the full composite view immediately — no configuration needed
3. All sections should show real data (health score, status bars, uptime %, alert counts)
4. Resize the widget — it should remain readable at 4×2 and look great at 6×3
5. Dark mode should work correctly (status bar colors, text contrast)

# Task 4: Threshold Configuration + Rendering

## Context

Every major IoT dashboard supports threshold-based color zones (e.g., "above 90 = red, 50-90 = yellow, below 50 = green"). Our widgets have zero threshold configuration.

## Step 1: Add threshold config UI to WidgetConfigDialog

**File:** `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

Add a **"Thresholds"** section after the Formatting section. Show it for: `kpi_tile`, `line_chart`, `bar_chart`, `gauge`, `health_score`, `device_count`.

```tsx
{/* === Thresholds Section === */}
{["kpi_tile", "line_chart", "bar_chart", "gauge", "health_score", "device_count"].includes(widgetType) && (
  <div className="border-t pt-4 space-y-3">
    <div className="flex items-center justify-between">
      <h4 className="text-sm font-medium">Thresholds</h4>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          const thresholds = (localConfig.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];
          setLocalConfig((c) => ({
            ...c,
            thresholds: [...thresholds, { value: 0, color: "#ef4444", label: "" }],
          }));
        }}
      >
        <Plus className="h-3 w-3 mr-1" /> Add
      </Button>
    </div>

    {((localConfig.thresholds as Array<{ value: number; color: string; label?: string }>) ?? []).map((t, i) => (
      <div key={i} className="flex items-center gap-2">
        <Input
          type="number"
          placeholder="Value"
          value={t.value}
          onChange={(e) => {
            const thresholds = [...((localConfig.thresholds as any[]) ?? [])];
            thresholds[i] = { ...thresholds[i], value: Number(e.target.value) };
            setLocalConfig((c) => ({ ...c, thresholds }));
          }}
          className="w-24"
        />
        <input
          type="color"
          value={t.color}
          onChange={(e) => {
            const thresholds = [...((localConfig.thresholds as any[]) ?? [])];
            thresholds[i] = { ...thresholds[i], color: e.target.value };
            setLocalConfig((c) => ({ ...c, thresholds }));
          }}
          className="h-8 w-8 cursor-pointer rounded border border-border"
        />
        <Input
          placeholder="Label (optional)"
          value={t.label ?? ""}
          onChange={(e) => {
            const thresholds = [...((localConfig.thresholds as any[]) ?? [])];
            thresholds[i] = { ...thresholds[i], label: e.target.value };
            setLocalConfig((c) => ({ ...c, thresholds }));
          }}
          className="flex-1"
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            const thresholds = ((localConfig.thresholds as any[]) ?? []).filter((_: unknown, j: number) => j !== i);
            setLocalConfig((c) => ({ ...c, thresholds }));
          }}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    ))}

    {((localConfig.thresholds as any[]) ?? []).length === 0 && (
      <p className="text-xs text-muted-foreground">No thresholds configured. Add one to color-code values.</p>
    )}
  </div>
)}
```

Import `Plus` and `X` from lucide-react if not already imported.

## Step 2: Render thresholds on line charts

**File:** `frontend/src/features/dashboard/widgets/renderers/LineChartRenderer.tsx`

Extract thresholds from config:
```typescript
const thresholds = (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];
```

Add `markLine` to the series in the ECharts option:

```typescript
series: [
  {
    type: "line",
    data: y,
    showSymbol: false,
    smooth: true,
    markLine: thresholds.length > 0 ? {
      silent: true,
      symbol: "none",
      data: thresholds.map((t) => ({
        yAxis: t.value,
        lineStyle: { color: t.color, type: "dashed", width: 1 },
        label: {
          show: !!t.label,
          formatter: t.label || "",
          position: "insideEndTop",
          fontSize: 10,
          color: t.color,
        },
      })),
    } : undefined,
  },
],
```

Add `thresholds` to the useMemo dependency array.

## Step 3: Render thresholds on bar charts

**File:** `frontend/src/features/dashboard/widgets/renderers/BarChartRenderer.tsx`

Same `markLine` pattern as line charts. Extract thresholds and add to the series:

```typescript
markLine: thresholds.length > 0 ? {
  silent: true,
  symbol: "none",
  data: thresholds.map((t) => ({
    yAxis: t.value,
    lineStyle: { color: t.color, type: "dashed", width: 1 },
    label: {
      show: !!t.label,
      formatter: t.label || "",
      position: "insideEndTop",
      fontSize: 10,
      color: t.color,
    },
  })),
} : undefined,
```

## Step 4: Render thresholds on gauges

**File:** `frontend/src/features/dashboard/widgets/renderers/GaugeRenderer.tsx`

For gauges, thresholds map to `axisLine` color zones. Sort thresholds by value and build color stops:

```typescript
const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];

// Build color zones for gauge axisLine
const sortedThresholds = [...thresholds].sort((a, b) => a.value - b.value);
const axisLineColors: [number, string][] = sortedThresholds.length > 0
  ? [
      ...sortedThresholds.map((t) => [t.value / max, t.color] as [number, string]),
      [1, "#22c55e"], // remaining segment = green (healthy)
    ]
  : []; // empty = use default theme gauge style

// In the gauge series config:
axisLine: {
  lineStyle: {
    width: 10,
    ...(axisLineColors.length > 0 ? { color: axisLineColors } : {}),
  },
},
```

## Step 5: Apply threshold colors to KPI tiles

**File:** `frontend/src/features/dashboard/widgets/renderers/KpiTileRenderer.tsx`

When thresholds are defined, color the KPI value based on which threshold it exceeds:

```typescript
const thresholds = (config.thresholds as Array<{ value: number; color: string }>) ?? [];

// Find the applicable threshold color (highest threshold the value exceeds)
const thresholdColor = useMemo(() => {
  if (thresholds.length === 0 || value === null) return undefined;
  const sorted = [...thresholds].sort((a, b) => b.value - a.value); // descending
  const match = sorted.find((t) => value >= t.value);
  return match?.color;
}, [thresholds, value]);
```

Apply to the value display:
```tsx
<span
  className="text-2xl font-semibold"
  style={thresholdColor ? { color: thresholdColor } : undefined}
>
  {formatted}
</span>
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

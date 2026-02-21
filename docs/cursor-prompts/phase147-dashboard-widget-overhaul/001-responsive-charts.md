# Task 1: Responsive Chart Sizing

## Context

All ECharts-based renderers pass fixed pixel heights via `style={{ height: 240 }}` or `style={{ height: 220 }}`. When a widget is resized smaller than this, the chart overflows or clips. The EChartWrapper already has a ResizeObserver that calls `chart.resize()` — but the fixed container heights prevent it from shrinking.

## Step 1: Update WidgetContainer to provide full height

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

The CardContent section already has `flex-1 overflow-auto`. This gives the content area all remaining height after the header. No changes needed here — the issue is in the renderers.

## Step 2: Remove fixed heights from ECharts renderers

For each file below, change the `<EChartWrapper>` style from a fixed pixel height to `height: "100%"`. Also add `className="h-full w-full"` and wrap in a container div if needed to ensure flexbox fills the parent.

### LineChartRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/LineChartRenderer.tsx`

Find the EChartWrapper render (approximately line 64):
```tsx
// BEFORE:
<EChartWrapper option={option} style={{ height: 240 }} />

// AFTER:
<div className="h-full w-full min-h-[120px]">
  <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
</div>
```

Also add `min-h-[120px]` to prevent charts from collapsing to zero in very small containers.

### BarChartRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/BarChartRenderer.tsx`

Same pattern:
```tsx
// BEFORE:
<EChartWrapper option={option} style={{ height: 240 }} />

// AFTER:
<div className="h-full w-full min-h-[120px]">
  <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
</div>
```

### GaugeRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/GaugeRenderer.tsx`

```tsx
// BEFORE:
<EChartWrapper option={option} style={{ height: 220 }} />

// AFTER:
<div className="h-full w-full min-h-[100px]">
  <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
</div>
```

### FleetStatusRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/FleetStatusRenderer.tsx`

```tsx
// BEFORE:
<EChartWrapper option={option} style={{ height: 220 }} />

// AFTER:
<div className="h-full w-full min-h-[100px]">
  <EChartWrapper option={option} style={{ width: "100%", height: "100%" }} />
</div>
```

## Step 3: Make HealthScoreRenderer responsive

**File:** `frontend/src/features/dashboard/widgets/renderers/HealthScoreRenderer.tsx`

The SVG is currently fixed at 120x120px. Change it to scale with its container:

```tsx
// BEFORE:
const size = 120;
const strokeWidth = 10;

// AFTER: use viewBox for responsive SVG
<div className="h-full flex items-center gap-4 px-2">
  <svg viewBox="0 0 120 120" className="h-full max-h-[120px] w-auto shrink-0">
    {/* Keep existing circle elements — they use the 120x120 coordinate space via viewBox */}
  </svg>
  <div className="flex flex-col gap-1 min-w-0">
    {/* stats text — keep existing */}
  </div>
</div>
```

Change the SVG `width` and `height` attributes to use `viewBox="0 0 120 120"` instead of fixed `width={120} height={120}`. Keep the internal `r`, `cx`, `cy`, `strokeWidth` values the same since they're now relative to the viewBox coordinate space.

## Step 4: Ensure EChartWrapper default height doesn't interfere

**File:** `frontend/src/lib/charts/EChartWrapper.tsx`

Check the default style (line ~68). It should be:
```tsx
style={{ height: 200, ...style }}
```

The explicit `style={{ width: "100%", height: "100%" }}` passed by renderers will override this default. No change needed if the spread is already there.

## Step 5: Update WidgetContainer CardContent

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

Ensure CardContent has `min-h-0` so flex children can shrink properly:
```tsx
// BEFORE:
<CardContent className="p-1.5 flex-1 overflow-auto">

// AFTER:
<CardContent className="p-1.5 flex-1 overflow-hidden min-h-0">
```

Change `overflow-auto` to `overflow-hidden` — chart containers should not show scrollbars; the chart should scale to fit.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task, verify: resize a widget to very small (2x2) and very large (6x4). The chart should fill the available space without clipping or scrollbars.

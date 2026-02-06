# Phase 27.6: Fix Gauge Colors for Light Theme

## Problem

Gauge value text is white (`#fafafa`) on white background in light mode — unreadable.

## Fix MetricGauge.tsx

**File:** `frontend/src/lib/charts/MetricGauge.tsx`

The gauge has hardcoded colors. Need to make them theme-aware.

Find the `detail` config (the big number in center):
```typescript
detail: {
  // ...
  color: "#fafafa",  // HARDCODED WHITE - BAD
}
```

**Option A: Use CSS variable via JavaScript**

```typescript
import { useUIStore } from "@/stores/ui-store";

function MetricGaugeInner({ metricName, value, allValues, className }: MetricGaugeProps) {
  const resolvedTheme = useUIStore((s) => s.resolvedTheme);

  // Theme-aware colors
  const textColor = resolvedTheme === "dark" ? "#fafafa" : "#18181b";
  const mutedColor = resolvedTheme === "dark" ? "#a1a1aa" : "#71717a";

  const option = useMemo<EChartsOption>(() => {
    return {
      series: [
        {
          // ... existing config ...
          axisLabel: {
            distance: 16,
            fontSize: 10,
            color: mutedColor,  // USE VARIABLE
            // ...
          },
          title: {
            offsetCenter: [0, "70%"],
            fontSize: 12,
            color: mutedColor,  // USE VARIABLE
          },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, "45%"],
            fontSize: 20,
            fontWeight: "bold",
            color: textColor,  // USE VARIABLE
            // ...
          },
          // ...
        },
      ],
    };
  }, [value, config, textColor, mutedColor]);  // ADD DEPENDENCIES

  // ...
}
```

**Option B: Simpler - just fix the hardcoded colors**

Find all hardcoded colors in the file and update:

| Property | Dark Mode | Light Mode |
|----------|-----------|------------|
| detail.color | #fafafa | #18181b |
| title.color | #a1a1aa | #71717a |
| axisLabel.color | #71717a | #52525b |
| splitLine.lineStyle.color | #52525b | #d4d4d8 |
| anchor.itemStyle.borderColor | #52525b | #d4d4d8 |

## Also Check UPlotChart and TimeSeriesChart

**File:** `frontend/src/lib/charts/TimeSeriesChart.tsx`

Look for hardcoded colors like:
```typescript
axes: [
  { stroke: "#71717a", grid: { stroke: "#27272a" } },  // HARDCODED
]
```

Make them theme-aware:
```typescript
const resolvedTheme = useUIStore((s) => s.resolvedTheme);
const axisColor = resolvedTheme === "dark" ? "#71717a" : "#52525b";
const gridColor = resolvedTheme === "dark" ? "#27272a" : "#e4e4e7";
```

## Rebuild and Test

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

Switch to light theme — gauge values should now be dark text on light background.

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/lib/charts/MetricGauge.tsx` |
| MODIFY | `frontend/src/lib/charts/TimeSeriesChart.tsx` |

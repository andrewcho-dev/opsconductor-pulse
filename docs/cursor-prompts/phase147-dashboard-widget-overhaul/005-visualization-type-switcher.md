# Task 5: Visualization Type Switcher

## Context

Users should be able to change how their data is displayed without recreating the widget. A line chart of temperature data should be switchable to a bar chart, gauge, or KPI tile — same data, different rendering.

## Architecture

Add a `display_as` field to widget config. When set, it overrides the widget's default renderer. The widget_type stays the same (preserving the data source config), but the renderer changes.

### Visualization Families

Define which widget types can switch to which renderers:

| Widget Type | Compatible Display Options |
|---|---|
| `line_chart` | line, bar |
| `bar_chart` | bar, line |
| `kpi_tile` | kpi, gauge |
| `gauge` | gauge, kpi |
| `table` | (no switching — display-specific) |
| `alert_feed` | (no switching — display-specific) |
| `fleet_status` | (no switching — see Task 7) |
| `device_count` | (no switching — see Task 7) |
| `health_score` | (no switching — see Task 7) |

## Step 1: Add display family mapping to widget-registry

**File:** `frontend/src/features/dashboard/widgets/widget-registry.ts`

Add a constant mapping widget types to their compatible display options:

```typescript
/** Maps widget types to the visualization types they can switch to */
export const DISPLAY_OPTIONS: Record<string, Array<{ value: string; label: string }>> = {
  line_chart: [
    { value: "line", label: "Line Chart" },
    { value: "bar", label: "Bar Chart" },
  ],
  bar_chart: [
    { value: "bar", label: "Bar Chart" },
    { value: "line", label: "Line Chart" },
  ],
  kpi_tile: [
    { value: "kpi", label: "KPI Tile" },
    { value: "gauge", label: "Gauge" },
  ],
  gauge: [
    { value: "gauge", label: "Gauge" },
    { value: "kpi", label: "KPI Tile" },
  ],
};

/** Maps display_as values to renderer component loaders */
const DISPLAY_RENDERERS: Record<string, () => Promise<{ default: ComponentType<WidgetRendererProps> }>> = {
  line: () => import("./renderers/LineChartRenderer"),
  bar: () => import("./renderers/BarChartRenderer"),
  kpi: () => import("./renderers/KpiTileRenderer"),
  gauge: () => import("./renderers/GaugeRenderer"),
};
```

Add a function to resolve the renderer for a widget:

```typescript
/**
 * Get the renderer component for a widget, respecting display_as override.
 */
export function getWidgetRenderer(
  widgetType: string,
  config: Record<string, unknown>
): () => Promise<{ default: ComponentType<WidgetRendererProps> }> {
  const displayAs = config.display_as as string | undefined;
  if (displayAs && DISPLAY_RENDERERS[displayAs]) {
    return DISPLAY_RENDERERS[displayAs];
  }
  const def = WIDGET_REGISTRY.get(widgetType);
  return def?.component ?? (() => import("./renderers/KpiTileRenderer"));
}
```

## Step 2: Update WidgetContainer to use display_as routing

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

Currently, the container loads the renderer via the widget definition's `component` field. Change it to use the new `getWidgetRenderer` function:

```tsx
// BEFORE:
const definition = getWidgetDefinition(widget.widget_type);
const Component = React.lazy(definition.component);

// AFTER:
import { getWidgetRenderer, getWidgetDefinition } from "./widget-registry";

const definition = getWidgetDefinition(widget.widget_type);
const rendererLoader = getWidgetRenderer(widget.widget_type, widget.config);
const Component = React.lazy(rendererLoader);
```

**Important:** The `React.lazy` call must be stable across re-renders. Wrap it in `useMemo`:

```tsx
const Component = useMemo(
  () => React.lazy(getWidgetRenderer(widget.widget_type, widget.config)),
  [widget.widget_type, widget.config]
);
```

This ensures the lazy component only re-creates when the widget type or config changes (including display_as).

## Step 3: Add "Display As" dropdown to WidgetConfigDialog

**File:** `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

Add a "Display As" dropdown at the TOP of the config dialog (before metric selection), but only for widget types that have display options:

```tsx
import { DISPLAY_OPTIONS } from "./widgets/widget-registry";

// Inside the dialog content, before existing config fields:
{DISPLAY_OPTIONS[widgetType] && (
  <div className="space-y-1">
    <Label htmlFor="display_as">Display As</Label>
    <Select
      value={(localConfig.display_as as string) ?? DISPLAY_OPTIONS[widgetType][0].value}
      onValueChange={(v) => setLocalConfig((c) => ({ ...c, display_as: v }))}
    >
      <SelectTrigger id="display_as">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {DISPLAY_OPTIONS[widgetType].map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
)}
```

## Step 4: Handle cross-type config compatibility

When switching from `line` to `gauge` display (via kpi_tile → gauge), the gauge renderer needs `min` and `max` config that the KPI tile doesn't have by default. Add sensible defaults in the renderers:

**GaugeRenderer.tsx** — already has defaults:
```typescript
const min = (config.min as number) ?? 0;
const max = (config.max as number) ?? 100;
```

**KpiTileRenderer.tsx** — when used as display_as target, it receives chart config (metric, time_range, devices) which it needs to handle. The KPI renderer already fetches data based on `config.metric`, so it should work. Verify that the metric values available in line_chart/bar_chart configs (`temperature`, `humidity`, etc.) are handled by the KPI renderer's data fetching logic. If not, add a fallback:

```typescript
// If the metric isn't in the KPI's built-in list, show "N/A" or the raw value
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task: create a line chart widget, open config, change "Display As" to "Bar Chart" — the widget should re-render as a bar chart with the same data.

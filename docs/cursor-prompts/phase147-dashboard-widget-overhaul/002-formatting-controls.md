# Task 2: Add Formatting Controls to Widget Config Dialog

## Context

The WidgetConfigDialog currently only offers metric selection, time range, and row limits. Users need formatting controls: decimal precision, axis visibility, legend toggle, Y-axis bounds, and title visibility.

## Step 1: Define the extended config type

**File:** `frontend/src/features/dashboard/widgets/widget-registry.ts`

Add a new interface after `WidgetRendererProps` (line ~21):

```typescript
/** Formatting options available in widget config */
export interface WidgetFormatConfig {
  /** Number of decimal places for numeric values (0-4, default: 1) */
  decimal_precision?: number;
  /** Hide the widget title bar (default: false) */
  show_title?: boolean;
  /** Show chart legend (default: true for charts) */
  show_legend?: boolean;
  /** Show X axis labels (default: true) */
  show_x_axis?: boolean;
  /** Show Y axis labels (default: true) */
  show_y_axis?: boolean;
  /** Y axis minimum value (auto if undefined) */
  y_axis_min?: number;
  /** Y axis maximum value (auto if undefined) */
  y_axis_max?: number;
  /** Override visualization type */
  display_as?: string;
  /** Threshold rules for color coding */
  thresholds?: Array<{ value: number; color: string; label?: string }>;
}
```

Export this interface so renderers can import it.

## Step 2: Add formatting section to WidgetConfigDialog

**File:** `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

After the existing config fields for each widget type (around line 210), add a **"Formatting"** section that appears for ALL widget types:

```tsx
{/* === Formatting Section === */}
<div className="border-t pt-4 space-y-3">
  <h4 className="text-sm font-medium">Formatting</h4>

  {/* Decimal Precision — show for KPI, gauge, health_score, device_count */}
  {["kpi_tile", "gauge", "health_score", "device_count", "line_chart", "bar_chart"].includes(widgetType) && (
    <div className="space-y-1">
      <Label htmlFor="decimal_precision">Decimal Places</Label>
      <Input
        id="decimal_precision"
        type="number"
        min={0}
        max={4}
        value={localConfig.decimal_precision ?? 1}
        onChange={(e) => setLocalConfig((c) => ({ ...c, decimal_precision: Number(e.target.value) }))}
      />
    </div>
  )}

  {/* Show Title toggle — all widget types */}
  <div className="flex items-center justify-between">
    <Label htmlFor="show_title">Show Title</Label>
    <Switch
      id="show_title"
      checked={localConfig.show_title !== false}
      onCheckedChange={(checked) => setLocalConfig((c) => ({ ...c, show_title: checked }))}
    />
  </div>

  {/* Chart-only formatting */}
  {["line_chart", "bar_chart", "fleet_status"].includes(widgetType) && (
    <>
      <div className="flex items-center justify-between">
        <Label htmlFor="show_legend">Show Legend</Label>
        <Switch
          id="show_legend"
          checked={localConfig.show_legend !== false}
          onCheckedChange={(checked) => setLocalConfig((c) => ({ ...c, show_legend: checked }))}
        />
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="show_x_axis">Show X Axis</Label>
        <Switch
          id="show_x_axis"
          checked={localConfig.show_x_axis !== false}
          onCheckedChange={(checked) => setLocalConfig((c) => ({ ...c, show_x_axis: checked }))}
        />
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="show_y_axis">Show Y Axis</Label>
        <Switch
          id="show_y_axis"
          checked={localConfig.show_y_axis !== false}
          onCheckedChange={(checked) => setLocalConfig((c) => ({ ...c, show_y_axis: checked }))}
        />
      </div>
    </>
  )}

  {/* Y-axis bounds — line and bar charts only */}
  {["line_chart", "bar_chart"].includes(widgetType) && (
    <div className="grid grid-cols-2 gap-2">
      <div className="space-y-1">
        <Label htmlFor="y_axis_min">Y Axis Min</Label>
        <Input
          id="y_axis_min"
          type="number"
          placeholder="Auto"
          value={localConfig.y_axis_min ?? ""}
          onChange={(e) => setLocalConfig((c) => ({
            ...c,
            y_axis_min: e.target.value === "" ? undefined : Number(e.target.value),
          }))}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="y_axis_max">Y Axis Max</Label>
        <Input
          id="y_axis_max"
          type="number"
          placeholder="Auto"
          value={localConfig.y_axis_max ?? ""}
          onChange={(e) => setLocalConfig((c) => ({
            ...c,
            y_axis_max: e.target.value === "" ? undefined : Number(e.target.value),
          }))}
        />
      </div>
    </div>
  )}
</div>
```

Add missing imports at the top of the file:
```tsx
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
```

Check if `Switch` and `Label` components exist. If `Switch` doesn't exist, use a checkbox-style toggle:
```tsx
<input type="checkbox" checked={...} onChange={...} className="..." />
```

Or generate the Switch component:
```bash
npx shadcn@latest add switch
```

## Step 3: Ensure localConfig handles new fields

In the WidgetConfigDialog, the `localConfig` state should already be `Record<string, unknown>` which can hold any key. Verify that the save mutation sends the full `localConfig` including new formatting fields. No changes should be needed here — the existing save logic sends the entire config object.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task: open a widget's config dialog and verify the new Formatting section appears with appropriate controls based on widget type.

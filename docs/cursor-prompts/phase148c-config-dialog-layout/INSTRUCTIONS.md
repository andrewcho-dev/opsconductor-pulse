# Phase 148c — Widget Config Dialog Layout Overhaul

## Problem

The WidgetConfigDialog is a 480px-wide single column that stacks up to 18 form fields vertically. For chart widgets it reaches ~900px of content height, overflowing the viewport on laptops. There is no logical grouping — formatting toggles, data source selectors, and thresholds are all in one flat list separated by thin lines. Switch toggles each occupy a full-width row, wasting space.

## Fix Overview

1. Widen dialog from 480px to 600px
2. Add Tabs (Data | Style | Thresholds) for complex widget types
3. Use compact 2-column grids for toggle switches and paired fields
4. Add ScrollArea to prevent viewport overflow
5. Simple widgets (table, alert_feed, fleet_overview) stay single-panel — no tabs needed

## File to Modify

`frontend/src/features/dashboard/WidgetConfigDialog.tsx` — complete restructure of the render layout. All state management, mutations, and config logic stay the same.

---

## Step 1: Add imports

Add these imports at the top of the file:

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
```

## Step 2: Widen the dialog

Change:
```tsx
<DialogContent className="sm:max-w-[480px]">
```
To:
```tsx
<DialogContent className="sm:max-w-[600px] max-h-[85vh] flex flex-col">
```

## Step 3: Determine which widgets need tabs

Add a helper near the top of the component function body (after `useDevices`):

```tsx
const widgetType = widget.widget_type;

// Widgets complex enough to need tabs
const needsTabs = [
  "line_chart", "bar_chart", "area_chart", "scatter", "radar",
  "kpi_tile", "stat_card", "gauge", "pie_chart",
].includes(widgetType);

// Widgets that support thresholds
const hasThresholds = [
  "kpi_tile", "line_chart", "bar_chart", "area_chart", "scatter",
  "gauge", "stat_card", "health_score", "device_count",
].includes(widgetType);
```

## Step 4: Restructure the dialog body

Replace the entire `<div className="space-y-4 py-4">` block (lines 545-848) with a tabbed or simple layout. The overall structure becomes:

```tsx
<div className="flex-1 overflow-hidden">
  {/* Title is always visible, outside tabs */}
  <div className="space-y-2 px-1 pt-4 pb-2">
    <Label>Title</Label>
    <Input
      value={title}
      onChange={(e) => setTitle(e.target.value)}
      placeholder="Widget title"
      maxLength={100}
    />
  </div>

  {needsTabs ? (
    <Tabs defaultValue="data" className="flex-1">
      <TabsList className="w-full">
        <TabsTrigger value="data">Data</TabsTrigger>
        <TabsTrigger value="style">Style</TabsTrigger>
        {hasThresholds && <TabsTrigger value="thresholds">Thresholds</TabsTrigger>}
      </TabsList>

      <ScrollArea className="h-[50vh] px-1">
        <TabsContent value="data" className="space-y-4 py-3">
          {renderDataTab()}
        </TabsContent>

        <TabsContent value="style" className="space-y-4 py-3">
          {renderStyleTab()}
        </TabsContent>

        {hasThresholds && (
          <TabsContent value="thresholds" className="space-y-3 py-3">
            {renderThresholdsTab()}
          </TabsContent>
        )}
      </ScrollArea>
    </Tabs>
  ) : (
    <ScrollArea className="h-[50vh] px-1">
      <div className="space-y-4 py-3">
        {renderConfigFields()}
      </div>
    </ScrollArea>
  )}
</div>
```

## Step 5: Create renderDataTab()

This renders data source controls. Replaces the top half of `renderConfigFields()`:

```tsx
function renderDataTab() {
  const statusDotClass = (status: string | undefined) => {
    if (status === "ONLINE") return "bg-status-online";
    if (status === "STALE") return "bg-status-warning";
    if (status === "OFFLINE") return "bg-status-critical";
    return "bg-muted-foreground";
  };

  // Display As (if applicable)
  const displayAsSection = DISPLAY_OPTIONS[widgetType] ? (
    <div className="space-y-2">
      <Label htmlFor="display_as">Display As</Label>
      <Select
        value={(config.display_as as string) ?? DISPLAY_OPTIONS[widgetType][0].value}
        onValueChange={(v) => updateConfig("display_as", v)}
      >
        <SelectTrigger id="display_as">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DISPLAY_OPTIONS[widgetType].map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  ) : null;

  // Device selector
  const deviceSection = ["line_chart", "bar_chart", "area_chart"].includes(widgetType) ? (
    <div className="space-y-2">
      <Label>Device</Label>
      <Select
        value={
          Array.isArray(config.devices) && (config.devices as string[]).length > 0
            ? (config.devices as string[])[0]
            : ""
        }
        onValueChange={(v) => updateConfig("devices", v ? [v] : [])}
        disabled={devicesLoading || devices.length === 0}
      >
        <SelectTrigger>
          <SelectValue
            placeholder={
              devicesLoading ? "Loading..." : devices.length === 0 ? "No devices" : "Select device"
            }
          />
        </SelectTrigger>
        <SelectContent>
          {devices.map((d) => (
            <SelectItem key={d.device_id} value={d.device_id}>
              <span className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`} />
                <span>{d.device_id}</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  ) : null;

  // --- Chart widgets (line, bar, area) ---
  if (["line_chart", "bar_chart", "area_chart"].includes(widgetType)) {
    return (
      <>
        {displayAsSection}
        {deviceSection}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || ""}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Time Range</Label>
            <Select
              value={(config.time_range as string) || "24h"}
              onValueChange={(v) => updateConfig("time_range", v)}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {TIME_RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </>
    );
  }

  // --- KPI tile ---
  if (widgetType === "kpi_tile") {
    return (
      <>
        {displayAsSection}
        <div className="space-y-2">
          <Label>Metric</Label>
          <Select
            value={(config.metric as string) || ""}
            onValueChange={(v) => updateConfig("metric", v)}
          >
            <SelectTrigger><SelectValue placeholder="Select metric" /></SelectTrigger>
            <SelectContent>
              {METRICS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </>
    );
  }

  // --- Stat card ---
  if (widgetType === "stat_card") {
    const sparklineDevice =
      typeof config.sparkline_device === "string" ? config.sparkline_device : "none";
    return (
      <>
        {displayAsSection}
        <div className="space-y-2">
          <Label>Metric</Label>
          <Select
            value={(config.metric as string) || "device_count"}
            onValueChange={(v) => updateConfig("metric", v)}
          >
            <SelectTrigger><SelectValue placeholder="Select metric" /></SelectTrigger>
            <SelectContent>
              {METRICS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Sparkline Device</Label>
          <Select
            value={sparklineDevice}
            onValueChange={(v) => updateConfig("sparkline_device", v === "none" ? undefined : v)}
            disabled={devicesLoading || devices.length === 0}
          >
            <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None</SelectItem>
              {devices.map((d) => (
                <SelectItem key={d.device_id} value={d.device_id}>
                  <span className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`} />
                    <span>{d.device_id}</span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </>
    );
  }

  // --- Gauge ---
  if (widgetType === "gauge") {
    return (
      <>
        {displayAsSection}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || "uptime_pct"}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Gauge Style</Label>
            <Select
              value={(config.gauge_style as string) ?? "arc"}
              onValueChange={(v) => updateConfig("gauge_style", v)}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="arc">Progress Arc</SelectItem>
                <SelectItem value="speedometer">Speedometer</SelectItem>
                <SelectItem value="ring">Ring</SelectItem>
                <SelectItem value="grade">Grade Bands</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Min</Label>
            <Input type="number" value={(config.min as number) ?? 0}
              onChange={(e) => updateConfig("min", Number(e.target.value))} />
          </div>
          <div className="space-y-2">
            <Label>Max</Label>
            <Input type="number" value={(config.max as number) ?? 100}
              onChange={(e) => updateConfig("max", Number(e.target.value))} />
          </div>
        </div>
      </>
    );
  }

  // --- Pie chart ---
  if (widgetType === "pie_chart") {
    return (
      <>
        <div className="space-y-2">
          <Label>Data Source</Label>
          <Select
            value={(config.pie_data_source as string) ?? "fleet_status"}
            onValueChange={(v) => updateConfig("pie_data_source", v)}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="fleet_status">Fleet Status</SelectItem>
              <SelectItem value="alert_severity">Alert Severity</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="doughnut">Donut Style</Label>
            <Switch id="doughnut"
              checked={(config.doughnut as boolean | undefined) ?? true}
              onCheckedChange={(c) => updateConfig("doughnut", c)} />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="show_labels">Show Labels</Label>
            <Switch id="show_labels"
              checked={(config.show_labels as boolean | undefined) ?? true}
              onCheckedChange={(c) => updateConfig("show_labels", c)} />
          </div>
        </div>
      </>
    );
  }

  // --- Scatter ---
  if (widgetType === "scatter") {
    return (
      <>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>X Axis Metric</Label>
            <Select value={(config.x_metric as string) || "temperature"}
              onValueChange={(v) => updateConfig("x_metric", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Y Axis Metric</Label>
            <Select value={(config.y_metric as string) || "humidity"}
              onValueChange={(v) => updateConfig("y_metric", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="space-y-2">
          <Label>Time Range</Label>
          <Select value={(config.time_range as string) || "24h"}
            onValueChange={(v) => updateConfig("time_range", v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {TIME_RANGES.map((r) => (
                <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </>
    );
  }

  // --- Radar ---
  if (widgetType === "radar") {
    const selectedMetrics = Array.isArray(config.radar_metrics)
      ? (config.radar_metrics as string[])
      : ["temperature", "humidity", "pressure"];
    return (
      <>
        <div className="space-y-2">
          <Label>Metrics (select 3–6)</Label>
          <div className="grid grid-cols-2 gap-1 max-h-[180px] overflow-y-auto">
            {METRICS.map((m) => {
              const isSelected = selectedMetrics.includes(m.value);
              const atLimit = selectedMetrics.length >= 6 && !isSelected;
              return (
                <label key={m.value}
                  className={`flex items-center gap-2 text-sm rounded px-2 py-1 cursor-pointer hover:bg-accent ${atLimit ? "opacity-50 cursor-not-allowed" : ""}`}>
                  <input type="checkbox" checked={isSelected} disabled={atLimit}
                    onChange={(e) => {
                      const newMetrics = e.target.checked
                        ? [...selectedMetrics, m.value]
                        : selectedMetrics.filter((x) => x !== m.value);
                      if (newMetrics.length >= 3) updateConfig("radar_metrics", newMetrics);
                    }}
                    className="rounded" />
                  {m.label}
                </label>
              );
            })}
          </div>
          {selectedMetrics.length < 3 && (
            <p className="text-xs text-destructive">Select at least 3 metrics</p>
          )}
        </div>
        <div className="space-y-2">
          <Label>Time Range</Label>
          <Select value={(config.time_range as string) || "24h"}
            onValueChange={(v) => updateConfig("time_range", v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {TIME_RANGES.map((r) => (
                <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </>
    );
  }

  return null;
}
```

## Step 6: Create renderStyleTab()

This renders all formatting and display controls in a compact layout:

```tsx
function renderStyleTab() {
  const isChart = ["line_chart", "bar_chart", "area_chart", "scatter", "radar", "pie_chart"].includes(widgetType);
  const isNumeric = ["kpi_tile", "gauge", "stat_card", "line_chart", "bar_chart", "area_chart"].includes(widgetType);
  const isLineArea = ["line_chart", "area_chart"].includes(widgetType);

  return (
    <>
      {/* Show/Hide toggles in compact 2-col grid */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Visibility</h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="show_title" className="text-sm">Title</Label>
            <Switch id="show_title"
              checked={(config.show_title as boolean | undefined) !== false}
              onCheckedChange={(c) => updateConfig("show_title", c)} />
          </div>
          {isChart && (
            <div className="flex items-center justify-between">
              <Label htmlFor="show_legend" className="text-sm">Legend</Label>
              <Switch id="show_legend"
                checked={(config.show_legend as boolean | undefined) !== false}
                onCheckedChange={(c) => updateConfig("show_legend", c)} />
            </div>
          )}
          {isChart && !["radar", "pie_chart"].includes(widgetType) && (
            <>
              <div className="flex items-center justify-between">
                <Label htmlFor="show_x_axis" className="text-sm">X Axis</Label>
                <Switch id="show_x_axis"
                  checked={(config.show_x_axis as boolean | undefined) !== false}
                  onCheckedChange={(c) => updateConfig("show_x_axis", c)} />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="show_y_axis" className="text-sm">Y Axis</Label>
                <Switch id="show_y_axis"
                  checked={(config.show_y_axis as boolean | undefined) !== false}
                  onCheckedChange={(c) => updateConfig("show_y_axis", c)} />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Numeric formatting */}
      {isNumeric && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Formatting</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="decimal_precision" className="text-sm">Decimal Places</Label>
              <Input id="decimal_precision" type="number" min={0} max={4}
                value={(config.decimal_precision as number) ?? 1}
                onChange={(e) => updateConfig("decimal_precision", Number(e.target.value))} />
            </div>
            {["line_chart", "bar_chart", "area_chart", "scatter"].includes(widgetType) && (
              <>
                <div />
                <div className="space-y-1">
                  <Label htmlFor="y_axis_min" className="text-sm">Y Axis Min</Label>
                  <Input id="y_axis_min" type="number" placeholder="Auto"
                    value={(config.y_axis_min as number | undefined) ?? ""}
                    onChange={(e) => updateConfig("y_axis_min", e.target.value === "" ? undefined : Number(e.target.value))} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="y_axis_max" className="text-sm">Y Axis Max</Label>
                  <Input id="y_axis_max" type="number" placeholder="Auto"
                    value={(config.y_axis_max as number | undefined) ?? ""}
                    onChange={(e) => updateConfig("y_axis_max", e.target.value === "" ? undefined : Number(e.target.value))} />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Chart sub-type toggles in compact grid */}
      {(isLineArea || widgetType === "bar_chart") && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Chart Options</h4>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            {isLineArea && (
              <>
                <div className="flex items-center justify-between">
                  <Label htmlFor="smooth" className="text-sm">Smooth</Label>
                  <Switch id="smooth"
                    checked={(config.smooth as boolean | undefined) ?? true}
                    onCheckedChange={(c) => updateConfig("smooth", c)} />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="step" className="text-sm">Step Line</Label>
                  <Switch id="step"
                    checked={(config.step as boolean | undefined) ?? false}
                    onCheckedChange={(c) => updateConfig("step", c)} />
                </div>
              </>
            )}
            {widgetType === "line_chart" && (
              <div className="flex items-center justify-between">
                <Label htmlFor="area_fill" className="text-sm">Area Fill</Label>
                <Switch id="area_fill"
                  checked={(config.area_fill as boolean | undefined) ?? false}
                  onCheckedChange={(c) => updateConfig("area_fill", c)} />
              </div>
            )}
            {widgetType === "area_chart" && (
              <div className="flex items-center justify-between">
                <Label htmlFor="stacked" className="text-sm">Stacked</Label>
                <Switch id="stacked"
                  checked={(config.stacked as boolean | undefined) ?? false}
                  onCheckedChange={(c) => updateConfig("stacked", c)} />
              </div>
            )}
            {widgetType === "bar_chart" && (
              <>
                <div className="flex items-center justify-between">
                  <Label htmlFor="stacked" className="text-sm">Stacked</Label>
                  <Switch id="stacked"
                    checked={(config.stacked as boolean | undefined) ?? false}
                    onCheckedChange={(c) => updateConfig("stacked", c)} />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="horizontal" className="text-sm">Horizontal</Label>
                  <Switch id="horizontal"
                    checked={(config.horizontal as boolean | undefined) ?? false}
                    onCheckedChange={(c) => updateConfig("horizontal", c)} />
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
```

## Step 7: Create renderThresholdsTab()

Extract the existing thresholds section into its own function. Keep the same logic but remove the border-top:

```tsx
function renderThresholdsTab() {
  return (
    <>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Add color thresholds to highlight when values cross boundaries.
        </p>
        <Button variant="outline" size="sm"
          onClick={() => {
            const thresholds = (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [];
            updateConfig("thresholds", [...thresholds, { value: 0, color: "#ef4444", label: "" }]);
          }}>
          <Plus className="h-3 w-3 mr-1" /> Add
        </Button>
      </div>

      {((config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? []).map((t, i) => (
        <div key={i} className="flex items-center gap-2">
          <Input type="number" placeholder="Value" value={t.value}
            onChange={(e) => {
              const thresholds = [...((config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [])];
              thresholds[i] = { ...thresholds[i], value: Number(e.target.value) };
              updateConfig("thresholds", thresholds);
            }}
            className="w-24" />
          <input type="color" value={t.color}
            onChange={(e) => {
              const thresholds = [...((config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [])];
              thresholds[i] = { ...thresholds[i], color: e.target.value };
              updateConfig("thresholds", thresholds);
            }}
            className="h-8 w-8 cursor-pointer rounded border border-border" />
          <Input placeholder="Label (optional)" value={t.label ?? ""}
            onChange={(e) => {
              const thresholds = [...((config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? [])];
              thresholds[i] = { ...thresholds[i], label: e.target.value };
              updateConfig("thresholds", thresholds);
            }}
            className="flex-1" />
          <Button variant="ghost" size="sm"
            onClick={() => {
              const thresholds = ((config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? []).filter((_, j) => j !== i);
              updateConfig("thresholds", thresholds);
            }}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      ))}

      {((config.thresholds as unknown[]) ?? []).length === 0 && (
        <p className="text-xs text-muted-foreground">
          No thresholds configured. Add one to color-code values.
        </p>
      )}
    </>
  );
}
```

## Step 8: Remove the old Display As section from the main render

The Display As dropdown is now inside `renderDataTab()`, so remove the standalone `{DISPLAY_OPTIONS[widget.widget_type] && ...}` block that was between the title and `renderConfigFields()`.

Also remove the old `{renderConfigFields()}` call, the old `{/* === Formatting Section === */}` block, and the old `{/* === Thresholds Section === */}` block — all replaced by the tab structure.

## Step 9: Keep renderConfigFields() for simple widgets only

The existing `renderConfigFields()` function is still used for simple widgets (table, alert_feed, fleet_overview) that don't use tabs. Keep ONLY the branches for:
- `fleet_overview` / `device_count` / `fleet_status` / `health_score`
- `table`
- `alert_feed`

Remove all other branches from `renderConfigFields()` — they're now in `renderDataTab()`.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

## Verify

1. Open config for a **line chart** widget → 3 tabs appear (Data | Style | Thresholds)
2. **Data tab**: Display As, Device, Metric + Time Range side-by-side
3. **Style tab**: Visibility toggles in 2-col grid, Decimal Places + Y bounds in 2-col, Chart Options in 2-col
4. **Thresholds tab**: clean list with Add button and rows
5. **Dialog fits on screen** — no overflow, scrollable content within tabs
6. Open config for a **gauge** widget → tabs with Metric + Style side-by-side, Min/Max side-by-side
7. Open config for a **table** widget → simple layout, no tabs (just Title + Rows)
8. Open config for a **radar** widget → metric checkboxes in 2-col grid
9. Open config for a **scatter** widget → X/Y metric selectors side-by-side
10. All save/cancel still works correctly
11. Dark mode renders correctly

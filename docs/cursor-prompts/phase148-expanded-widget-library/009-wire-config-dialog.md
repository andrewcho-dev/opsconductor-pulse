# Task 9: Expand Config Dialog

## Context

Tasks 1-8 added new renderers and registered them. Now the WidgetConfigDialog needs to support configuring all new widget types and sub-type options.

## Step 1: Add gauge style picker

**File:** `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

In the `renderConfigFields()` function, update the `gauge` branch to include a gauge style selector:

```tsx
if (widgetType === "gauge") {
  return (
    <>
      <div className="space-y-2">
        <Label>Metric</Label>
        <Select
          value={(config.metric as string) || "uptime_pct"}
          onValueChange={(v) => updateConfig("metric", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
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
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="arc">Progress Arc</SelectItem>
            <SelectItem value="speedometer">Speedometer</SelectItem>
            <SelectItem value="ring">Ring</SelectItem>
            <SelectItem value="grade">Grade Bands</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Min</Label>
          <Input
            type="number"
            value={(config.min as number) ?? 0}
            onChange={(e) => updateConfig("min", Number(e.target.value))}
          />
        </div>
        <div className="space-y-2">
          <Label>Max</Label>
          <Input
            type="number"
            value={(config.max as number) ?? 100}
            onChange={(e) => updateConfig("max", Number(e.target.value))}
          />
        </div>
      </div>
    </>
  );
}
```

## Step 2: Add chart sub-type toggles

In the Formatting section, add chart sub-type toggles for applicable widget types. Add these INSIDE the existing formatting `<div className="border-t pt-4 space-y-3">` section, after the existing Y Axis Min/Max controls:

```tsx
{/* Chart sub-type toggles */}
{["line_chart", "area_chart"].includes(widget.widget_type) && (
  <>
    <div className="flex items-center justify-between">
      <Label htmlFor="smooth">Smooth Curves</Label>
      <Switch
        id="smooth"
        checked={(config.smooth as boolean | undefined) ?? true}
        onCheckedChange={(checked) => updateConfig("smooth", checked)}
      />
    </div>
    <div className="flex items-center justify-between">
      <Label htmlFor="step">Step Line</Label>
      <Switch
        id="step"
        checked={(config.step as boolean | undefined) ?? false}
        onCheckedChange={(checked) => updateConfig("step", checked)}
      />
    </div>
    {widget.widget_type === "line_chart" && (
      <div className="flex items-center justify-between">
        <Label htmlFor="area_fill">Area Fill</Label>
        <Switch
          id="area_fill"
          checked={(config.area_fill as boolean | undefined) ?? false}
          onCheckedChange={(checked) => updateConfig("area_fill", checked)}
        />
      </div>
    )}
    {widget.widget_type === "area_chart" && (
      <div className="flex items-center justify-between">
        <Label htmlFor="stacked">Stacked</Label>
        <Switch
          id="stacked"
          checked={(config.stacked as boolean | undefined) ?? false}
          onCheckedChange={(checked) => updateConfig("stacked", checked)}
        />
      </div>
    )}
  </>
)}

{widget.widget_type === "bar_chart" && (
  <>
    <div className="flex items-center justify-between">
      <Label htmlFor="stacked">Stacked</Label>
      <Switch
        id="stacked"
        checked={(config.stacked as boolean | undefined) ?? false}
        onCheckedChange={(checked) => updateConfig("stacked", checked)}
      />
    </div>
    <div className="flex items-center justify-between">
      <Label htmlFor="horizontal">Horizontal</Label>
      <Switch
        id="horizontal"
        checked={(config.horizontal as boolean | undefined) ?? false}
        onCheckedChange={(checked) => updateConfig("horizontal", checked)}
      />
    </div>
  </>
)}
```

## Step 3: Add stat card config

In `renderConfigFields()`, add a case for `stat_card`:

```tsx
if (widgetType === "stat_card") {
  return (
    <>
      <div className="space-y-2">
        <Label>Metric</Label>
        <Select
          value={(config.metric as string) || "device_count"}
          onValueChange={(v) => updateConfig("metric", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
```

## Step 4: Add pie chart config

In `renderConfigFields()`, add a case for `pie_chart`:

```tsx
if (widgetType === "pie_chart") {
  return (
    <>
      <div className="space-y-2">
        <Label>Data Source</Label>
        <Select
          value={(config.pie_data_source as string) ?? "fleet_status"}
          onValueChange={(v) => updateConfig("pie_data_source", v)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="fleet_status">Fleet Status</SelectItem>
            <SelectItem value="alert_severity">Alert Severity</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="doughnut">Donut Style</Label>
        <Switch
          id="doughnut"
          checked={(config.doughnut as boolean | undefined) ?? true}
          onCheckedChange={(checked) => updateConfig("doughnut", checked)}
        />
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="show_labels">Show Labels</Label>
        <Switch
          id="show_labels"
          checked={(config.show_labels as boolean | undefined) ?? true}
          onCheckedChange={(checked) => updateConfig("show_labels", checked)}
        />
      </div>
    </>
  );
}
```

## Step 5: Add scatter config

In `renderConfigFields()`, add a case for `scatter`:

```tsx
if (widgetType === "scatter") {
  return (
    <>
      <div className="space-y-2">
        <Label>X Axis Metric</Label>
        <Select
          value={(config.x_metric as string) || "temperature"}
          onValueChange={(v) => updateConfig("x_metric", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select X metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Y Axis Metric</Label>
        <Select
          value={(config.y_metric as string) || "humidity"}
          onValueChange={(v) => updateConfig("y_metric", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select Y metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
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
          <SelectTrigger>
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            {TIME_RANGES.map((r) => (
              <SelectItem key={r.value} value={r.value}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
```

## Step 6: Add radar config

In `renderConfigFields()`, add a case for `radar`. This uses a checkbox group for metric selection:

```tsx
if (widgetType === "radar") {
  const selectedMetrics = Array.isArray(config.radar_metrics)
    ? (config.radar_metrics as string[])
    : ["temperature", "humidity", "pressure"];

  return (
    <>
      <div className="space-y-2">
        <Label>Metrics (select 3-6)</Label>
        <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
          {METRICS.map((m) => {
            const isSelected = selectedMetrics.includes(m.value);
            const atLimit = selectedMetrics.length >= 6 && !isSelected;
            return (
              <label
                key={m.value}
                className={`flex items-center gap-2 text-sm rounded px-2 py-1 cursor-pointer hover:bg-accent ${atLimit ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  disabled={atLimit}
                  onChange={(e) => {
                    const newMetrics = e.target.checked
                      ? [...selectedMetrics, m.value]
                      : selectedMetrics.filter((x) => x !== m.value);
                    if (newMetrics.length >= 3) {
                      updateConfig("radar_metrics", newMetrics);
                    }
                  }}
                  className="rounded"
                />
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
        <Select
          value={(config.time_range as string) || "24h"}
          onValueChange={(v) => updateConfig("time_range", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            {TIME_RANGES.map((r) => (
              <SelectItem key={r.value} value={r.value}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
```

## Step 7: Update formatting section applicability

The decimal places input should also apply to `stat_card`. Update the condition:

Change:
```tsx
{["kpi_tile", "gauge", "health_score", "device_count", "line_chart", "bar_chart"].includes(widget.widget_type) && (
```

To:
```tsx
{["kpi_tile", "gauge", "stat_card", "health_score", "device_count", "line_chart", "bar_chart", "area_chart"].includes(widget.widget_type) && (
```

The legend/axis toggles should also apply to `area_chart`, `scatter`, and `radar`. Update:

Change:
```tsx
{["line_chart", "bar_chart", "fleet_status"].includes(widget.widget_type) && (
```

To:
```tsx
{["line_chart", "bar_chart", "area_chart", "scatter", "radar", "pie_chart", "fleet_status"].includes(widget.widget_type) && (
```

The Y axis min/max should apply to area and scatter too. Update:

Change:
```tsx
{["line_chart", "bar_chart"].includes(widget.widget_type) && (
```

To:
```tsx
{["line_chart", "bar_chart", "area_chart", "scatter"].includes(widget.widget_type) && (
```

The thresholds section should also apply to new types. Update:

Change:
```tsx
{["kpi_tile", "line_chart", "bar_chart", "gauge", "health_score", "device_count"].includes(widget.widget_type) && (
```

To:
```tsx
{["kpi_tile", "line_chart", "bar_chart", "area_chart", "scatter", "gauge", "stat_card", "health_score", "device_count"].includes(widget.widget_type) && (
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task: open any widget config dialog and verify:
- Gauge widgets show a "Gauge Style" dropdown with 4 options
- Line charts show smooth/step/area-fill toggles
- Bar charts show stacked/horizontal toggles
- Pie chart shows data source and donut toggle
- Scatter shows X/Y metric selectors
- Radar shows metric checkboxes

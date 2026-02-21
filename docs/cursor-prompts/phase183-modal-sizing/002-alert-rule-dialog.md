# Task 2: AlertRuleDialog Overhaul

## Objective

Restructure the AlertRuleDialog to fit its content without scrolling, using a wider dialog and multi-column layout.

## File to Modify

`frontend/src/features/alerts/AlertRuleDialog.tsx`

## Current Problems

1. **Width:** Default `sm:max-w-lg` (512px) — way too narrow for the content
2. **Rule mode buttons:** 5 full `<Button>` elements in a `flex` row overflow 512px
3. **All fields stacked vertically:** Creates a very tall form
4. **Forced scroll:** `max-h-[85vh] overflow-y-auto` on DialogContent
5. **Multi-condition grid:** `md:grid-cols-[1fr_210px_120px_160px_auto]` is wider than 512px

## Changes

### 1. Widen the dialog

Change the `DialogContent` className:

```tsx
// OLD:
<DialogContent className="max-h-[85vh] overflow-y-auto">

// NEW:
<DialogContent className="sm:max-w-3xl">
```

Remove the `max-h-[85vh] overflow-y-auto`. At 768px wide with 2-column layouts, the content should fit without forced scrolling for most rule modes. If some modes are still tall, add `max-h-[90vh] overflow-y-auto` as a safety net, but try without it first.

### 2. Compact rule mode selector

Replace the 5 `<Button>` row with a `Select` dropdown:

```tsx
// OLD: 5 buttons in a flex row
<div className="grid gap-2">
  <Label>Rule Mode</Label>
  <div className="flex gap-2">
    <Button ... >Simple Rule</Button>
    <Button ... >Multi-Condition Rule</Button>
    <Button ... >Anomaly Detection</Button>
    <Button ... >Data Gap</Button>
    <Button ... >Window Aggregation</Button>
  </div>
</div>

// NEW: Select dropdown
<FormField
  control={form.control}
  name="ruleMode"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Rule Mode</FormLabel>
      <Select
        value={field.value}
        onValueChange={(v) => {
          field.onChange(v);
          // Keep the existing logic for initializing conditions when switching to "multi"
          if (v === "multi") {
            const existing = form.getValues("conditions") ?? [];
            if (existing.length === 0) {
              form.setValue(
                "conditions",
                [{ metric_name: "", operator: "GT", threshold: 0, duration_minutes: null }],
                { shouldDirty: true }
              );
            }
            form.setValue("match_mode", "all", { shouldDirty: false });
          }
        }}
      >
        <FormControl>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
        </FormControl>
        <SelectContent>
          <SelectItem value="simple">Simple Threshold</SelectItem>
          <SelectItem value="multi">Multi-Condition</SelectItem>
          <SelectItem value="anomaly">Anomaly Detection</SelectItem>
          <SelectItem value="gap">Data Gap</SelectItem>
          <SelectItem value="window">Window Aggregation</SelectItem>
        </SelectContent>
      </Select>
      <FormMessage />
    </FormItem>
  )}
/>
```

### 3. Two-column grid for common fields

After the rule-specific section, arrange the common fields in a 2-column grid where possible:

```tsx
{/* Row 1: Severity + Duration side by side */}
<div className="grid gap-4 sm:grid-cols-2">
  <FormField name="severity" ... />
  <FormField name="duration_minutes" ... />
</div>

{/* Row 2: Device Group Scope (full width) */}
<FormField name="device_group_id" ... />

{/* Row 3: Device Groups checkboxes (full width) */}
<FormField name="group_ids" ... />

{/* Row 4: Description (full width) */}
<FormField name="description" ... />

{/* Row 5: Enabled toggle (full width) */}
<FormField name="enabled" ... />
```

### 4. Two-column layout for simple mode fields

In simple mode, when targeting by metric, put Operator and Threshold side by side:

```tsx
{/* After metric select: */}
<div className="grid gap-4 sm:grid-cols-2">
  <FormField name="operator" ... />
  <FormField name="threshold" ... />
</div>
```

### 5. Two-column layout for anomaly mode

Put the 4 anomaly fields in a 2×2 grid:

```tsx
<div className="space-y-3 rounded-md border border-border p-3">
  <FormField name="anomaly_metric_name" ... />
  <div className="grid gap-4 sm:grid-cols-2">
    <FormField name="anomaly_window_minutes" ... />
    <FormField name="anomaly_z_threshold" ... />
  </div>
  <FormField name="anomaly_min_samples" ... />
</div>
```

### 6. Two-column layout for window mode

```tsx
<div className="space-y-3 rounded-md border border-border p-3">
  <FormField name="metric_name" ... />
  <div className="grid gap-4 sm:grid-cols-2">
    <FormField name="window_aggregation" ... />
    <FormField name="window_seconds" ... />
  </div>
  <div className="grid gap-4 sm:grid-cols-2">
    <FormField name="operator" ... />
    <FormField name="threshold" ... />
  </div>
</div>
```

### 7. Name + Rule Mode on same row

Put the Rule Name and Rule Mode side by side at the top of the form:

```tsx
<div className="grid gap-4 sm:grid-cols-2">
  <FormField name="name" ... />
  {/* Rule Mode Select */}
</div>
```

### 8. Template selector row

If templates exist (create mode only), put the template selector in a compact row above the form, not taking full width of a stacked layout.

## Summary of Layout

After restructure, the simple mode form fits roughly in this layout (at 768px):

```
┌──────────────────────────────────────────┐
│ Create Alert Rule                         │
│ Define threshold conditions that trigger  │
│                                          │
│ [Template: ▼ Select template]  (if any)  │
│                                          │
│ [Rule Name          ] [Rule Mode    ▼]   │
│                                          │
│ ┌─ Simple Threshold ───────────────────┐ │
│ │ [Targeting  ▼ By metric name      ]  │ │
│ │ [Metric Name        ▼            ]   │ │
│ │ [Operator ▼ ]  [Threshold       ]    │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ [Severity   ▼ ]  [Duration (min)     ]   │
│ [Scope to Device Group       ▼       ]   │
│ [Device Groups checkboxes...         ]   │
│ [Description                         ]   │
│ [Enabled ─────────────────── toggle  ]   │
│                                          │
│              [Cancel]  [Create Rule]     │
└──────────────────────────────────────────┘
```

This should fit in one viewport at 768px wide without scrolling for simple, anomaly, gap, and window modes. Multi-condition mode with many conditions may still scroll — that's acceptable since the number of conditions is user-controlled.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- AlertRuleDialog opens at 768px wide
- Simple mode fits in one viewport without scrolling
- Anomaly mode fits without scrolling (4 fields in 2×2 grid)
- Gap mode fits without scrolling (2 fields)
- Window mode fits without scrolling (5 fields in 2-column grid)
- Multi-condition mode may scroll with 3+ conditions — acceptable
- Rule mode is a Select dropdown, not 5 buttons
- Operator + Threshold are side by side
- Severity + Duration are side by side
- All form validation still works
- Dirty guard still works

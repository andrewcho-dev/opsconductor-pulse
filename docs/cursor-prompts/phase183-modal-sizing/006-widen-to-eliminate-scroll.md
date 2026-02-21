# Task 6: Widen AlertRuleDialog and EditTenantDialog to Eliminate Scrolling

## Problem

Tasks 2-3 used `sm:max-w-3xl` (768px) and `max-w-2xl` (672px) respectively. Even with 2-column grids, the forms are still taller than the viewport and require scrolling. The goal is **zero scrolling** for standard form states.

The fix: go wider (1024px) and use 3-column grids where possible so the form height fits in one viewport.

---

## 1. AlertRuleDialog

**File:** `frontend/src/features/alerts/AlertRuleDialog.tsx`

### A. Widen from `sm:max-w-3xl` to `sm:max-w-5xl`

```tsx
// OLD (line 697):
<DialogContent className="sm:max-w-3xl">

// NEW:
<DialogContent className="sm:max-w-5xl">
```

`sm:max-w-5xl` = 1024px. At this width, 3-column grids give ~300px per column — plenty for label + input.

### B. Pack common fields into fewer rows

Currently the bottom section (after the rule-specific block) is:

```
Row 1: Severity + Duration           (2-col)
Row 2: Device Group Scope            (full width)
Row 3: Device Groups checkboxes      (full width)
Row 4: Description textarea          (full width)
Row 5: Enabled toggle                (full width)
```

Change to:

```
Row 1: Severity + Duration + Scope   (3-col)
Row 2: Device Groups checkboxes      (full width — only if groups exist)
Row 3: Description + Enabled         (2-col)
```

#### Row 1: Severity + Duration + Scope in 3-column grid

Replace the current 2-column Severity/Duration grid (lines ~1462-1512) AND the full-width Device Group Scope field (lines ~1514-1544) with a single 3-column grid:

```tsx
<div className="grid gap-4 sm:grid-cols-3">
  {/* Severity */}
  <FormField
    control={form.control}
    name="severity"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Severity</FormLabel>
        <Select value={String(field.value ?? 3)} onValueChange={(v) => field.onChange(Number(v))}>
          <FormControl>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select severity" />
            </SelectTrigger>
          </FormControl>
          <SelectContent>
            <SelectItem value="1">1 (Info)</SelectItem>
            <SelectItem value="2">2 (Low)</SelectItem>
            <SelectItem value="3">3 (Medium)</SelectItem>
            <SelectItem value="4">4 (High)</SelectItem>
            <SelectItem value="5">5 (Critical)</SelectItem>
          </SelectContent>
        </Select>
        <FormMessage />
      </FormItem>
    )}
  />

  {/* Duration */}
  <FormField
    control={form.control}
    name="duration_minutes"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Duration (min)</FormLabel>
        <FormControl>
          <Input
            type="number"
            min={1}
            step={1}
            placeholder="Instant"
            value={field.value == null ? "" : String(field.value)}
            onChange={field.onChange}
          />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />

  {/* Scope to Device Group */}
  <FormField
    control={form.control}
    name="device_group_id"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Scope to Group</FormLabel>
        <Select
          value={(field.value as string) || "none"}
          onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
        >
          <FormControl>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="All devices" />
            </SelectTrigger>
          </FormControl>
          <SelectContent>
            <SelectItem value="none">All devices</SelectItem>
            {(deviceGroupsResponse?.groups ?? []).map((group: DeviceGroup) => (
              <SelectItem key={group.group_id} value={group.group_id}>
                {group.name} ({group.member_count ?? 0})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <FormMessage />
      </FormItem>
    )}
  />
</div>
```

**Important:** Remove the `FormDescription` text from both the Duration field and the Scope field. The labels are self-explanatory at this width. Removing the descriptions saves significant vertical space.

#### Row 3: Description + Enabled on same row

Replace the current full-width Description field (lines ~1585-1597) and full-width Enabled toggle (lines ~1599-1610) with a 2-column grid:

```tsx
<div className="grid gap-4 sm:grid-cols-2">
  {/* Description */}
  <FormField
    control={form.control}
    name="description"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Description</FormLabel>
        <FormControl>
          <Textarea placeholder="Optional context for this rule" rows={2} {...field} />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />

  {/* Enabled toggle */}
  <FormField
    control={form.control}
    name="enabled"
    render={({ field }) => (
      <div className="flex items-center justify-between rounded-md border border-border p-3 self-end">
        <div>
          <Label className="text-sm">Enabled</Label>
          <p className="text-sm text-muted-foreground">Alerts trigger when enabled.</p>
        </div>
        <Switch checked={Boolean(field.value)} onCheckedChange={field.onChange} />
      </div>
    )}
  />
</div>
```

### C. Simple mode: Targeting + Metric on one row

In simple mode with "By metric name" targeting, put the Targeting select and Metric Name select side by side instead of stacked:

Find the section starting at line ~798 where `ruleMode === "simple"` renders. Currently it has:
1. Targeting select (full width)
2. Metric Name select (full width, when targeting === "metric")
3. Operator + Threshold (2-col)

Change to put Targeting and Metric side by side when targeting mode is "metric":

```tsx
{ruleMode === "simple" ? (
  <>
    {targetingMode === "metric" ? (
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Targeting select */}
        <FormField
          control={form.control}
          name="targeting_mode"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Targeting</FormLabel>
              <Select
                value={(field.value as string) || "metric"}
                onValueChange={(v) => {
                  field.onChange(v);
                  if (v === "metric") {
                    form.setValue("sensor_device_id", "", { shouldDirty: true });
                    form.setValue("sensor_id", null, { shouldDirty: true });
                    form.setValue("sensor_type", "", { shouldDirty: true });
                  } else if (v === "sensor") {
                    form.setValue("sensor_type", "", { shouldDirty: true });
                    form.setValue("metric_name", "", { shouldDirty: true });
                  } else if (v === "sensor_type") {
                    form.setValue("sensor_device_id", "", { shouldDirty: true });
                    form.setValue("sensor_id", null, { shouldDirty: true });
                    form.setValue("metric_name", "", { shouldDirty: true });
                  }
                }}
              >
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select targeting mode" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="metric">By metric name</SelectItem>
                  <SelectItem value="sensor">By specific sensor</SelectItem>
                  <SelectItem value="sensor_type">By sensor type</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Metric Name select — keep entire existing FormField as-is, just inside this grid */}
        <FormField ... name="metric_name" ... />
      </div>
    ) : (
      <>
        {/* For sensor/sensor_type targeting, keep existing stacked layout */}
        <FormField name="targeting_mode" ... />
        {targetingMode === "sensor" ? ( ... ) : ( ... )}
      </>
    )}

    {/* Operator + Threshold stay as 2-col grid — no change */}
    <div className="grid gap-4 sm:grid-cols-2">
      <FormField name="operator" ... />
      <FormField name="threshold" ... />
    </div>
  </>
)
```

**Note:** When moving the Metric Name FormField into the 2-col grid, remove the tooltip/info icon and `FormDescription` from it. Those extras add height. The metric selector's SelectContent already shows normalized vs raw grouping — that's sufficient context at 1024px.

### D. Template selector in same row as Name + Mode

In create mode, put the template selector alongside Name and Rule Mode in a 3-column row:

```tsx
// Currently: Template selector is a full-width row, then Name + Mode is a 2-col row
// Change to: one 3-column row

{!isEditing && templates.length > 0 ? (
  <div className="grid gap-4 sm:grid-cols-3">
    {/* Template */}
    <div className="grid gap-2">
      <Label>Template</Label>
      <Select ... >...</Select>
    </div>
    {/* Name */}
    <FormField name="name" ... />
    {/* Rule Mode */}
    <FormField name="ruleMode" ... />
  </div>
) : (
  <div className="grid gap-4 sm:grid-cols-2">
    {/* Name */}
    <FormField name="name" ... />
    {/* Rule Mode */}
    <FormField name="ruleMode" ... />
  </div>
)}
```

### Expected layout after changes (simple + metric targeting):

```
┌──────────────────────────────────────────────────────────────────┐
│ Create Alert Rule                                                │
│ Define threshold conditions that trigger alerts.                 │
│                                                                  │
│ [Template    ▼]  [Rule Name         ]  [Rule Mode     ▼]       │
│                                                                  │
│ ┌─ Simple Threshold ───────────────────────────────────────────┐│
│ │ [Targeting ▼ By metric]  [Metric Name              ▼]       ││
│ │ [Operator  ▼]            [Threshold                ]        ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│ [Severity ▼]  [Duration (min)   ]  [Scope to Group      ▼]     │
│ [Device Groups checkboxes...                                ]   │
│ [Description               ]  [Enabled ──────── toggle    ]    │
│                                                                  │
│                              [Cancel]  [Create Rule]            │
└──────────────────────────────────────────────────────────────────┘
```

Height estimate: ~8 vertical slots × ~65px + header ~80px + footer ~60px = ~660px. Fits in 85vh (918px on 1080p) with room to spare.

---

## 2. EditTenantDialog

**File:** `frontend/src/features/operator/EditTenantDialog.tsx`

### A. Widen from `max-w-2xl` to `sm:max-w-5xl`

```tsx
// OLD (line 205):
<DialogContent className="max-w-2xl">

// NEW:
<DialogContent className="sm:max-w-5xl">
```

### B. Lay out fieldsets in a 2-column grid

Currently the 4 fieldsets are stacked vertically. Put them in a 2×2 grid:

Replace the current `<form>` inner layout. Wrap the fieldsets in a 2-column grid:

```tsx
<form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
  <div className="grid gap-4 sm:grid-cols-2">
    {/* Left column */}
    <div className="space-y-4">
      {/* Basic Info fieldset — keep as-is */}
      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Basic Info</legend>
        ...existing 3 rows of 2-col grids (Display Name + Legal Name, Contact Name + Contact Email, Phone + Billing Email)...
      </fieldset>

      {/* Company Details fieldset — keep as-is */}
      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Company Details</legend>
        ...existing 1 row of 2-col grid (Industry + Company Size)...
      </fieldset>
    </div>

    {/* Right column */}
    <div className="space-y-4">
      {/* Address fieldset — keep as-is */}
      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Address</legend>
        ...existing 3 rows (Address 1 + Address 2, City + State, Postal Code + Country)...
      </fieldset>

      {/* Operations fieldset — keep as-is */}
      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Operations</legend>
        ...existing rows (Region + Support Tier, SLA + Stripe ID, Status)...
      </fieldset>
    </div>
  </div>

  {/* Footer stays full width below */}
  <div className="flex justify-end gap-2 pt-4">
    <Button type="button" variant="outline" onClick={handleClose}>Cancel</Button>
    <Button type="submit" disabled={mutation.isPending}>
      {mutation.isPending ? "Saving..." : "Save Changes"}
    </Button>
  </div>

  {mutation.isError && (
    <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
  )}
</form>
```

The internal content of each fieldset stays exactly the same (the existing 2-col grids within each fieldset). You're just wrapping the 4 fieldsets in a 2-column outer grid instead of stacking them vertically.

### Expected layout:

```
┌────────────────────────────────────────────────────────────────────┐
│ Edit Tenant: tenant-abc-123                                        │
│                                                                    │
│ ┌─ Basic Info ────────────────┐ ┌─ Address ─────────────────────┐ │
│ │ [Display Name] [Legal Name] │ │ [Address Line 1] [Address 2 ] │ │
│ │ [Contact Name] [Cont Email] │ │ [City         ] [State      ] │ │
│ │ [Phone       ] [Bill Email] │ │ [Postal Code  ] [Country    ] │ │
│ └─────────────────────────────┘ └───────────────────────────────┘ │
│ ┌─ Company Details ───────────┐ ┌─ Operations ─────────────────┐ │
│ │ [Industry ▼ ] [Size     ▼ ]│ │ [Region    ▼ ] [Support  ▼ ] │ │
│ └─────────────────────────────┘ │ [SLA Level   ] [Stripe ID  ] │ │
│                                  │ [Status ▼                  ] │ │
│                                  └───────────────────────────────┘ │
│                                                                    │
│                                    [Cancel]  [Save Changes]       │
└────────────────────────────────────────────────────────────────────┘
```

Height estimate: ~5 row heights for the taller column (Address + Operations) × ~65px + fieldset chrome ~60px + header ~80px + footer ~60px = ~505px. No scrolling.

---

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- AlertRuleDialog opens at 1024px, simple mode fits in one viewport without scrolling
- EditTenantDialog opens at 1024px, all 4 fieldsets visible at once in 2×2 grid, no scrolling
- Anomaly/gap/window modes in AlertRuleDialog also fit without scrolling
- Multi-condition mode may still scroll with 4+ conditions — acceptable (user-controlled content)
- All form validation and dirty guards still work
- No TypeScript errors

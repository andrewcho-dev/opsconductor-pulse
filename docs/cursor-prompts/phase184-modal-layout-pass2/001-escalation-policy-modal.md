# Task 1: EscalationPolicyModal Restructure

## File

`frontend/src/features/escalation/EscalationPolicyModal.tsx`

## Current Problems

1. `max-w-4xl` (896px) — OK width but poorly used
2. Name + Default checkbox on one row, Description below — wastes a full row
3. Escalation levels use `md:grid-cols-12` packing 5 fields into one horizontal line per level — cramped, "Level" column wastes space for a single digit
4. No field labels on the level grid items — just muted text headers above each cell

## Changes

### A. Widen to `sm:max-w-5xl` (1024px)

```tsx
// OLD:
<DialogContent className="max-w-4xl">

// NEW:
<DialogContent className="sm:max-w-5xl">
```

### B. Pack header: Name + Timezone-row + Default on one row

Put Name, Description, and Default checkbox in a smarter layout:

```tsx
// Replace the current header section (lines 148-179) with:

<div className="grid gap-4 sm:grid-cols-3">
  <div className="sm:col-span-2 space-y-2">
    <label className="text-sm font-medium">Policy Name</label>
    <Input
      value={form.name}
      onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
      placeholder="Default Escalation Policy"
    />
  </div>
  <div className="flex items-end gap-2 pb-1">
    <Checkbox
      checked={form.is_default}
      onCheckedChange={(checked) =>
        setForm((prev) => ({ ...prev, is_default: checked === true }))
      }
      id="is-default-policy"
    />
    <label htmlFor="is-default-policy" className="text-sm">
      Default policy for new alert rules
    </label>
  </div>
</div>

<div className="space-y-2">
  <label className="text-sm font-medium">Description</label>
  <Textarea
    value={form.description}
    onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
    placeholder="Optional context for this policy"
    rows={2}
  />
</div>
```

### C. Restructure escalation levels as compact cards

Replace the `md:grid-cols-12` grid (lines 190-253) with a cleaner card layout. Each level becomes a bordered card with labeled fields in a clean grid:

```tsx
{form.levels.map((level, idx) => (
  <div key={idx} className="rounded-md border border-border p-4">
    <div className="flex items-center justify-between mb-3">
      <div className="text-sm font-medium">Level {idx + 1}</div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => removeLevel(idx)}
        disabled={form.levels.length <= 1}
        className="h-7 text-muted-foreground"
      >
        Remove
      </Button>
    </div>
    <div className="grid gap-4 sm:grid-cols-4">
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Delay (min)</label>
        <Input
          type="number"
          min={1}
          value={level.delay_minutes}
          onChange={(e) => updateLevel(idx, { delay_minutes: Number(e.target.value || 1) })}
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Notify Email</label>
        <Input
          placeholder="notify@example.com"
          value={level.notify_email ?? ""}
          onChange={(e) => updateLevel(idx, { notify_email: e.target.value })}
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Webhook URL</label>
        <Input
          placeholder="https://..."
          value={level.notify_webhook ?? ""}
          onChange={(e) => updateLevel(idx, { notify_webhook: e.target.value })}
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">On-Call Schedule</label>
        <Select
          value={level.oncall_schedule_id != null ? String(level.oncall_schedule_id) : "none"}
          onValueChange={(v) =>
            updateLevel(idx, { oncall_schedule_id: v === "none" ? undefined : Number(v) })
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="None" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            {(schedulesQuery.data?.schedules ?? []).map((schedule) => (
              <SelectItem key={schedule.schedule_id} value={String(schedule.schedule_id)}>
                {schedule.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  </div>
))}
```

At 1024px, `sm:grid-cols-4` gives ~230px per column — enough for each labeled field. The Level number + Remove button are in a header row above the fields, not wasting a grid column.

### Expected Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ New Escalation Policy                                            │
│                                                                  │
│ [Policy Name                          ]  [✓ Default policy...]  │
│ [Description (optional)                                       ] │
│                                                                  │
│ Escalation Levels                              [Add Level]      │
│ ┌─ Level 1 ──────────────────────────────────── [Remove] ──────┐│
│ │ Delay(min) | Notify Email      | Webhook URL   | On-Call ▼  ││
│ │ [15      ] | [ops@example.com] | [https://...] | [Sched ▼]  ││
│ └──────────────────────────────────────────────────────────────┘│
│ ┌─ Level 2 ──────────────────────────────────── [Remove] ──────┐│
│ │ [30      ] | [mgr@example.com] | [           ] | [None  ▼]  ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│                              [Cancel]  [Save]                   │
└──────────────────────────────────────────────────────────────────┘
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Modal opens at 1024px
- Header row has Name + Default checkbox side by side
- Each escalation level is a clear bordered card with labeled fields in 4-col grid
- All fields have labels
- Add/Remove level still works
- Form submission still works

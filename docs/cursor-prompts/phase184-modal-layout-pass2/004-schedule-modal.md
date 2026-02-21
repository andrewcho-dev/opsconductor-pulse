# Task 4: ScheduleModal Restructure

## File

`frontend/src/features/oncall/ScheduleModal.tsx`

## Current Problems

1. `max-w-4xl` (896px) — decent width but wasted
2. Name, Description, Timezone each take a full row — 3 rows for header info
3. Layer config uses `md:grid-cols-4` with 4 unlabeled number inputs (rotation type, shift hours, handoff day, handoff hour) — user has no idea what each number means
4. Responder list with ↑/↓ buttons takes significant vertical space

## Changes

### A. Widen to `sm:max-w-5xl` (1024px)

```tsx
// OLD:
<DialogContent className="max-w-4xl">

// NEW:
<DialogContent className="sm:max-w-5xl">
```

### B. Pack header: Name + Timezone on one row, Description below

Replace lines 72-90:

```tsx
<div className="grid gap-4 sm:grid-cols-3">
  <div className="sm:col-span-2 space-y-1">
    <label className="text-sm font-medium">Schedule Name</label>
    <Input
      placeholder="Primary On-Call"
      value={name}
      onChange={(e) => setName(e.target.value)}
    />
  </div>
  <div className="space-y-1">
    <label className="text-sm font-medium">Timezone</label>
    <Select value={timezone} onValueChange={setTimezone}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select timezone" />
      </SelectTrigger>
      <SelectContent>
        {ZONES.map((zone) => (
          <SelectItem key={zone} value={zone}>{zone}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
</div>

<div className="space-y-1">
  <label className="text-sm font-medium">Description</label>
  <Textarea
    placeholder="Optional description"
    value={description}
    onChange={(e) => setDescription(e.target.value)}
    rows={2}
  />
</div>
```

### C. Label all layer fields and use 3-column grid

Replace the layer config section (lines 92-231). Each layer becomes a bordered card with properly labeled fields:

```tsx
{layers.map((layer, idx) => (
  <div key={idx} className="rounded-md border border-border p-4 space-y-3">
    <div className="flex items-center justify-between">
      <Input
        placeholder="Layer name"
        value={layer.name}
        className="max-w-xs"
        onChange={(e) =>
          setLayers((prev) => prev.map((item, i) => (i === idx ? { ...item, name: e.target.value } : item)))
        }
      />
      {layers.length > 1 && (
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
          onClick={() => setLayers((prev) => prev.filter((_, i) => i !== idx).map((l, i) => ({ ...l, layer_order: i })))}
        >
          Remove
        </Button>
      )}
    </div>

    <div className="grid gap-4 sm:grid-cols-4">
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Rotation</label>
        <Select
          value={layer.rotation_type}
          onValueChange={(v) =>
            setLayers((prev) =>
              prev.map((item, i) =>
                i === idx ? { ...item, rotation_type: v as OncallLayer["rotation_type"] } : item
              )
            )
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="daily">Daily</SelectItem>
            <SelectItem value="weekly">Weekly</SelectItem>
            <SelectItem value="custom">Custom</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Shift Duration (hrs)</label>
        <Input
          type="number"
          min={1}
          value={layer.shift_duration_hours}
          onChange={(e) =>
            setLayers((prev) =>
              prev.map((item, i) =>
                i === idx ? { ...item, shift_duration_hours: Number(e.target.value) || 1 } : item
              )
            )
          }
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Handoff Day (0-6)</label>
        <Input
          type="number"
          min={0}
          max={6}
          value={layer.handoff_day}
          onChange={(e) =>
            setLayers((prev) =>
              prev.map((item, i) =>
                i === idx ? { ...item, handoff_day: Number(e.target.value) || 0 } : item
              )
            )
          }
        />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Handoff Hour (0-23)</label>
        <Input
          type="number"
          min={0}
          max={23}
          value={layer.handoff_hour}
          onChange={(e) =>
            setLayers((prev) =>
              prev.map((item, i) =>
                i === idx ? { ...item, handoff_hour: Number(e.target.value) || 0 } : item
              )
            )
          }
        />
      </div>
    </div>

    {/* Responders — inline list */}
    <div className="space-y-2">
      <label className="text-xs font-medium text-muted-foreground">Responders</label>
      {layer.responders.map((responder, rIdx) => (
        <div key={rIdx} className="flex gap-2">
          <Input
            placeholder="responder email/name"
            value={responder}
            onChange={(e) =>
              setLayers((prev) =>
                prev.map((item, i) =>
                  i === idx
                    ? {
                        ...item,
                        responders: item.responders.map((entry, ri) =>
                          ri === rIdx ? e.target.value : entry
                        ),
                      }
                    : item
                )
              )
            }
          />
          {/* Keep existing ↑/↓ buttons */}
          <Button variant="outline" size="sm" disabled={rIdx === 0} onClick={...}>↑</Button>
          <Button variant="outline" size="sm" disabled={rIdx === layer.responders.length - 1} onClick={...}>↓</Button>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={...}>Add Responder</Button>
    </div>
  </div>
))}
```

### Expected Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ New Schedule                                                     │
│                                                                  │
│ [Schedule Name                          ]  [Timezone        ▼]  │
│ [Description (optional)                                       ] │
│                                                                  │
│ ┌─ [Layer 1              ] ──────────────────── [Remove] ──────┐│
│ │ Rotation | Shift Dur(hrs) | Handoff Day(0-6) | Handoff Hr   ││
│ │ [Weekly▼]| [168         ] | [1              ] | [9         ] ││
│ │                                                              ││
│ │ Responders                                                   ││
│ │ [alice@example.com                           ] [↑] [↓]      ││
│ │ [bob@example.com                             ] [↑] [↓]      ││
│ │ [Add Responder]                                              ││
│ └──────────────────────────────────────────────────────────────┘│
│ [Add Layer]                                                     │
│                                                                  │
│                              [Cancel]  [Save]                   │
└──────────────────────────────────────────────────────────────────┘
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Modal opens at 1024px
- Name + Timezone on same row
- Layer fields have labels (Rotation, Shift Duration, Handoff Day, Handoff Hour)
- Responder ↑/↓ reordering still works
- Add/Remove layer still works
- Form submission still works

# Task 1: Compact Expansion Modules Section

## File to Modify

`frontend/src/features/devices/DeviceSensorsDataTab.tsx`

## Change

Replace the expansion modules rendering (the `<div className="grid gap-3">` block that maps over `slots`) with a compact single-table layout.

### Find this block (approximately lines 669-715):

The block that starts with:
```tsx
<div className="grid gap-3">
  {slots.map((slot) => {
```

And ends with the closing `</div>` of that grid.

### Replace with:

```tsx
<div className="rounded-md border border-border divide-y divide-border">
  {slots.map((slot) => {
    const assigned = modules.filter((m) => m.slot_key === slot.slot_key && m.status !== "removed");
    const max = slot.max_devices ?? null;
    const countText = max != null ? `${assigned.length}/${max}` : `${assigned.length}`;
    const canAssign = max == null || assigned.length < max;
    return (
      <div key={slot.id}>
        {/* Slot row — compact single line */}
        <div className="flex items-center gap-2 px-3 py-2">
          <code className="text-xs text-muted-foreground">{slot.slot_key}</code>
          <span className="text-sm font-medium">{slot.display_name}</span>
          {slotBadge(slot)}
          {slot.is_required && <Badge variant="destructive" className="text-[10px] px-1 py-0">required</Badge>}
          <span className="ml-auto text-xs text-muted-foreground">{countText}</span>
          {canAssign ? (
            <AssignModuleDialog
              deviceId={deviceId}
              slot={slot}
              moduleTemplates={moduleTemplates}
              onDone={() => {}}
            />
          ) : (
            <Badge variant="secondary" className="text-xs">Full</Badge>
          )}
        </div>
        {/* Assigned modules — indented sub-rows, only if any */}
        {assigned.length > 0 && (
          <div className="border-t border-border bg-muted/30 px-3 py-2">
            <DataTable
              columns={moduleColumns}
              data={assigned}
              isLoading={modulesQuery.isLoading}
              manualPagination={false}
            />
          </div>
        )}
      </div>
    );
  })}
</div>
```

### Key changes:

1. **Single bordered container** — one `rounded-md border` wrapping all slots, with `divide-y` between them. NOT one card per slot.
2. **Each slot is one compact row** — `flex items-center gap-2 px-3 py-2`. Slot key, name, type badge, count, and action button all on one line.
3. **"No modules assigned" text is gone** — the count (`0/1`) is self-explanatory. No need for a separate empty-state line per slot.
4. **Assigned modules appear ONLY when present** — as an indented sub-area with `bg-muted/30` background below the slot row. The DataTable only renders when `assigned.length > 0`.
5. **"At capacity" button replaced with simple badge** — `<Badge variant="secondary">Full</Badge>` instead of a disabled button.
6. **Assign Module button is now `size="sm"`** — already is from the AssignModuleDialog, so it fits inline.

### Also: Make the "Assign Module" button smaller

The `AssignModuleDialog` component's trigger button (defined near line 130-133 in the same file) currently uses:
```tsx
<Button size="sm">Assign Module</Button>
```

Change it to be more compact:
```tsx
<Button size="sm" variant="outline" className="h-7 text-xs">Assign</Button>
```

This shortens the label from "Assign Module" to "Assign" and makes the button smaller with `h-7 text-xs`.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- All 4 module slots visible in a compact stacked list (~100px total, not ~400px)
- Each slot is a single row: key + name + badge + count + button
- No "No modules assigned" text on empty slots
- Assigned modules (when present) show in a sub-area below the slot row
- Assign dialog still works correctly
- Sensors table and telemetry charts are now visible without scrolling past modules

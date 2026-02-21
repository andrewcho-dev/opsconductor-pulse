# Task 1: Collapse Empty Expansion Modules

## File to Modify

`frontend/src/features/devices/DeviceSensorsDataTab.tsx`

## Change

Replace the entire `<section className="space-y-3">` block for Expansion Modules (the first `<section>` in the return, approximately lines 652–718) with a collapsible version that hides empty slots by default and constrains width.

### Replace the entire Expansion Modules section with:

```tsx
<section>
  {!templateId ? (
    <div className="rounded border border-border p-3 text-sm text-muted-foreground">
      No template assigned. Assign a template to enable expansion modules.
    </div>
  ) : slots.length === 0 ? null : (() => {
    const totalAssigned = modules.filter((m) => m.status !== "removed").length;
    const hasAssignments = totalAssigned > 0;
    return (
      <details open={hasAssignments || undefined} className="group">
        <summary className="flex cursor-pointer items-center gap-2 py-2 text-sm [&::-webkit-details-marker]:hidden">
          <span className="text-xs text-muted-foreground transition-transform group-open:rotate-90">&#9654;</span>
          <span className="font-semibold">Expansion Modules</span>
          <span className="text-muted-foreground">
            — {slots.length} slots, {totalAssigned} assigned
          </span>
        </summary>
        <div className="mt-2 max-w-2xl divide-y divide-border rounded-md border border-border">
          {slots.map((slot) => {
            const assigned = modules.filter(
              (m) => m.slot_key === slot.slot_key && m.status !== "removed"
            );
            const max = slot.max_devices ?? null;
            const countText = max != null ? `${assigned.length}/${max}` : `${assigned.length}`;
            const canAssign = max == null || assigned.length < max;
            return (
              <div key={slot.id}>
                <div className="flex items-center gap-2 px-3 py-1.5">
                  <code className="text-xs text-muted-foreground">{slot.slot_key}</code>
                  <span className="text-sm">{slot.display_name}</span>
                  {slotBadge(slot)}
                  {slot.is_required && (
                    <Badge variant="destructive" className="px-1 py-0 text-[10px]">
                      required
                    </Badge>
                  )}
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
      </details>
    );
  })()}
</section>
```

### Key changes:

1. **`<details>` element** — The entire slot list is inside a collapsible `<details>`.
   - When `totalAssigned === 0`: closed by default (no `open` attribute). User sees one line: "▸ Expansion Modules — 4 slots, 0 assigned".
   - When `totalAssigned > 0`: open by default (`open` attribute set).

2. **`max-w-2xl`** on the slot list container — constrains width to 672px so rows don't stretch across the full 1200px page. The count and Assign button stay near the slot name instead of floating to the far right.

3. **Summary line uses `[&::-webkit-details-marker]:hidden`** to hide the browser's default disclosure triangle. A custom `▸` character rotates via `group-open:rotate-90`.

4. **"This template has no slots defined" case removed** — if `slots.length === 0`, render nothing. No need to announce the absence of something.

5. **Row padding reduced** from `py-2` to `py-1.5` for even more compactness.

6. **Section header ("Expansion Modules" + description) removed** — the `<summary>` line replaces it. No more separate header + description taking up space.

### Important note on the IIFE:

The `(() => { ... })()` pattern (immediately invoked function expression) is used because `<details>` needs to compute `totalAssigned` before rendering. If you prefer, you can extract this into a small inline component instead. Either approach works.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- When 0 modules assigned: section is ONE LINE, closed by default ("▸ Expansion Modules — 4 slots, 0 assigned")
- Clicking the summary expands to show slots, constrained to max-w-2xl
- When modules are assigned: section is open by default
- Slot list is ~672px wide, not full-width
- Assign dialog still works
- Sensors table and telemetry charts immediately visible (no scrolling past empty modules)

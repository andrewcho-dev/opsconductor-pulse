# Task 1: Device List, Filters, and Detail Panels

## Objective

Replace all raw `<select>`, `<input type="checkbox">`, and `<button>` elements in the device list page, filter components, and device detail sub-panels with shadcn/ui equivalents.

Refer to `000-start.md` for migration rules and import references.

## Files to Modify (7)

---

### 1. `frontend/src/features/devices/DeviceListPage.tsx`

**Raw `<select>` violations:**
- **~Line 174** — Device status filter dropdown (All/Online/Offline/Stale) in the sidebar filter panel
- **~Line 190** — Site filter dropdown in the sidebar filter panel

Replace each `<select>` + `<option>` block with `Select` + `SelectTrigger` + `SelectValue` + `SelectContent` + `SelectItem`. Use `"all"` as the sentinel value for "All" options, and convert back to empty string in `onValueChange` if the state uses `""`.

**Raw `<button>` violations:**
- **~Line 216** — Device card clickable item (navigates to device detail). Replace with `<Link>` styled as a card, or `<Button variant="ghost" asChild><Link to={...}>`.
- **~Lines 265, 277** — Prev/Next pagination buttons. Replace with `<Button variant="outline" size="icon-sm">`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue` from `@/components/ui/select`; `Button` from `@/components/ui/button` (if not already imported).

---

### 2. `frontend/src/features/devices/DeviceFilters.tsx`

This file has the most violations — it contains an inline `PaginationControls` sub-component and multiple filter controls.

**Raw `<select>` violations:**
- **~Line 34** — Page size selector (100/250/500/1000) inside the `PaginationControls` inline function
- **~Line 171** — Device status filter (All/Online/Stale/Offline)

Replace with `Select` components. For page size: `onValueChange={(v) => setPageSize(Number(v))}`.

**Raw `<input type="checkbox">` violations:**
- **~Line 237** — Per-tag checkbox in the tag filter panel (multi-select list of tags)

Replace with `Checkbox` component (this is a multi-select list pattern, not a toggle).

**Raw `<button>` violations:**
- **~Lines 51, 59, 67, 75** — First/Prev/Next/Last pagination buttons inside `PaginationControls`
- **~Line 154** — "Clear search" × button inside the search input
- **~Line 215** — "Clear tag filters" button

Replace all with `Button` components. Pagination buttons: `variant="outline" size="icon-sm"`. Clear buttons: `variant="ghost" size="icon-sm"`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Checkbox`; `Button` (if not already imported).

---

### 3. `frontend/src/features/devices/DeviceAlertsSection.tsx`

**Raw `<select>` violations:**
- **~Line 100** — Silence duration picker (15m/30m/1h/4h/24h) rendered inline on each alert row

Replace with `Select`. Use compact sizing: `<SelectTrigger className="w-[80px] h-7">`.

**Raw `<button>` violations:**
- **~Lines 71, 83, 92, 111** — Acknowledge, Close, Silence, and Apply-silence action buttons on alert rows

Replace all with `Button variant="ghost" size="sm"` or `Button variant="outline" size="sm"`. Destructive actions (Close) can use `variant="ghost"` with `className="text-destructive"`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Button`.

---

### 4. `frontend/src/features/devices/DeviceInfoCard.tsx`

**Raw `<button>` violations:**
- **~Line 59** — Edit pencil icon button on the device info card
- **~Line 136** — Per-tag "×" remove button

Replace with `Button variant="ghost" size="icon-sm"`.

**Add imports:** `Button`.

---

### 5. `frontend/src/features/devices/DeviceDetailPane.tsx`

**Raw `<button>` violations:**
- **~Line 130** — "Decommission" option inside a custom `<details>`/`<summary>` dropdown

If this is a dropdown with dangerous actions, consider replacing the `<details>`/`<summary>` with a `DropdownMenu` + `DropdownMenuItem`. If that's too large a change, at minimum replace the inner `<button>` with `Button variant="ghost"`.

**Add imports:** `Button`.

---

### 6. `frontend/src/features/devices/DeviceUptimePanel.tsx`

**Raw `<button>` violations:**
- **~Line 30** — Time range toggle buttons (24h/7d/30d)

These are mutually-exclusive options acting as a toggle group. Replace with `Button variant="outline" size="sm"` for each option, with the active option using `variant="default"` or a conditional `className` for the selected state (e.g., `variant={range === "24h" ? "default" : "outline"}`).

**Add imports:** `Button`.

---

### 7. `frontend/src/features/devices/DevicePlanPanel.tsx`

**Raw `<button>` violations:**
- **~Line 204** — Plan option cards (each device plan is a clickable `<button>` in the change-plan dialog)

Replace with `Button variant="outline"` styled as a card, or use `<div role="button" tabIndex={0}>` → `Button variant="ghost" className="h-auto w-full justify-start text-left p-3"`. The selected plan can use a different variant or border color.

**Add imports:** `Button`.

---

## Verification

After all changes:

```bash
cd frontend && npx tsc --noEmit
```

- All 7 files compile without errors
- No raw `<select>`, `<input type="checkbox">`, or `<button>` remains in any of the 7 files
- Device list page renders correctly with styled filter dropdowns
- Pagination controls use design system buttons
- Device detail panels use design system buttons for actions
- Dark mode renders correctly for all replaced elements

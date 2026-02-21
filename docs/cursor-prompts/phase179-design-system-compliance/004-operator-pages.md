# Task 4: Operator Pages + Activity Log

## Objective

Replace all raw `<select>`, `<button>` elements in operator-facing pages (NOC, user detail, audit log, tenant health matrix) and the customer activity log page.

Refer to `000-start.md` for migration rules and import references.

## Files to Modify (5)

---

### 1. `frontend/src/features/operator/noc/NOCPage.tsx`

**Raw `<select>` violations:**
- **~Line 103** — Auto-refresh interval selector (15s/30s/60s) in the NOC dashboard toolbar

Replace with `Select`. Use compact sizing: `<SelectTrigger className="w-[80px] h-8">`.

**Raw `<button>` violations:**
- **~Line 112** — Pause/Resume toggle button in the NOC toolbar
- **~Line 119** — TV Mode toggle button

Replace both with `Button`. The Pause/Resume button should toggle its label/icon based on state:
```tsx
<Button variant="outline" size="sm" onClick={togglePause}>
  {paused ? <Play className="mr-1 h-3.5 w-3.5" /> : <Pause className="mr-1 h-3.5 w-3.5" />}
  {paused ? "Resume" : "Pause"}
</Button>
```

TV Mode button:
```tsx
<Button variant={tvMode ? "default" : "outline"} size="sm" onClick={toggleTvMode}>
  <Monitor className="mr-1 h-3.5 w-3.5" />
  TV Mode
</Button>
```

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Button`.

---

### 2. `frontend/src/features/operator/UserDetailPage.tsx`

**Raw `<select>` violations:**
- **~Line 198** — Role picker when assigning a new role to a user (dropdown of available roles)

Replace with `Select`.

**Raw `<button>` violations:**
- **~Line 186** — "Remove" role button (small × inside a role badge)

Replace with `Button variant="ghost" size="icon-sm"`. This is a small inline action button.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Button` (if not already imported).

---

### 3. `frontend/src/features/operator/AuditLogPage.tsx`

This file has an inline `PaginationControls` sub-component with both raw selects and raw buttons.

**Raw `<select>` violations:**
- **~Line 47** — Page size selector inside the `PaginationControls` inline function

Replace with `Select`.

**Raw `<button>` violations:**
- **~Lines 58, 59, 60, 61** — First/Prev/Next/Last pagination buttons inside `PaginationControls`
- **~Line 186** — Expand/collapse JSON details button on each audit log row

Replace pagination buttons with `Button variant="outline" size="icon-sm"`. The expand/collapse button should be `Button variant="ghost" size="icon-sm"`.

For pagination, use consistent icon sizing:
```tsx
<Button variant="outline" size="icon-sm" onClick={() => setPage(0)} disabled={page === 0}>
  <ChevronsLeft className="h-3.5 w-3.5" />
</Button>
<Button variant="outline" size="icon-sm" onClick={() => setPage(page - 1)} disabled={page === 0}>
  <ChevronLeft className="h-3.5 w-3.5" />
</Button>
```

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Button` (if not already imported). May need to add `ChevronsLeft, ChevronsRight` from lucide-react if not already imported.

---

### 4. `frontend/src/features/operator/TenantHealthMatrix.tsx`

**Raw `<select>` violations:**
- **~Line 157** — Sort-by selector (alerts/devices/lastActive/name) for the tenant health matrix grid

Replace with `Select`. Use a descriptive placeholder: `<SelectValue placeholder="Sort by..." />`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 5. `frontend/src/features/audit/ActivityLogPage.tsx`

This file has the same inline `PaginationControls` pattern as `AuditLogPage.tsx`.

**Raw `<select>` violations:**
- **~Line 63** — Page size selector inside the `PaginationControls` inline function

Replace with `Select`.

**Raw `<button>` violations:**
- **~Lines 79, 86, 93, 100** — First/Prev/Next/Last pagination buttons inside `PaginationControls`
- **~Line 309** — Expand/collapse JSON details button per event row

Replace with `Button` components using the same pattern as AuditLogPage above.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Button` (if not already imported).

---

## Verification

After all changes:

```bash
cd frontend && npx tsc --noEmit
```

- All 5 files compile without errors
- No raw `<select>` or `<button>` remains in any of the 5 files
- NOC page toolbar shows styled controls (refresh interval dropdown, pause/resume and TV mode buttons)
- User detail page shows styled role picker and remove buttons
- Audit log pages show styled pagination with design system buttons and page-size dropdown
- Tenant health matrix shows styled sort dropdown
- Dark mode renders correctly for all replaced elements

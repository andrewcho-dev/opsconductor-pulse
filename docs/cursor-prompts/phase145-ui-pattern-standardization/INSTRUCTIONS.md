# Phase 145 — Cursor Execution Instructions

Execute these 10 tasks **in order**. Each task depends on the previous one completing successfully. After each task, run `cd frontend && npx tsc --noEmit` to catch errors before moving on.

**Important:** This phase changes HOW UI elements are used, not their visual styling. Keep all existing functionality — only change the presentation patterns.

---

## Task 1: Fix dashboard actions

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/001-fix-dashboard-actions.md` for full details.

Move the "Edit Layout" / "Lock Layout" toggle and "Add Widget" button from the DashboardBuilder content area into the DashboardSettings gear dropdown menu.

Key changes:
1. Lift `isEditing` and `showAddWidget` state from DashboardBuilder up to DashboardPage
2. Add "Edit Layout" and "Add Widget" as menu items in DashboardSettings dropdown
3. Remove the standalone toolbar div from DashboardBuilder
4. Pass `isEditing`, `onToggleEdit`, `onAddWidget` props through the component tree
5. Keep the layout save/flush logic working on edit→lock transition

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 2: Standardize page headers

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/002-standardize-page-headers.md` for full details.

Make ALL pages use the `<PageHeader>` component:
1. **OperatorDashboard.tsx** — replace custom `text-2xl font-semibold` heading with PageHeader
2. **SystemDashboard.tsx** — move Pause/Play/Refresh/interval controls into PageHeader `action` prop, replace raw `<button>`/`<select>` with `<Button>`/`<Select>` components
3. **CertificateOverviewPage.tsx** — replace custom `<h1>` with PageHeader

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 3: Standardize create buttons

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/003-standardize-create-buttons.md` for full details.

ALL create/add buttons → `Plus` icon + `"Add {Noun}"` label:
- `"+ New Campaign"` → `<Plus /> Add Campaign`
- `"+ Register Firmware"` → `<Plus /> Add Firmware`
- `"+ Create Job"` → `<Plus /> Add Job`
- `"New Role"` → `<Plus /> Add Role`
- `"Invite User"` → `<Plus /> Add User`
- `"Create Tenant"` → `<Plus /> Add Tenant`
- Buttons already saying "Add X" just need the Plus icon added

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 4: Add breadcrumbs to detail pages

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/004-add-breadcrumbs.md` for full details.

Add breadcrumbs to ALL detail pages that are missing them:
1. **OtaCampaignDetailPage.tsx** — `OTA Campaigns > {name}`
2. **OperatorTenantDetailPage.tsx** — `Tenants > {name}` + move Edit button into PageHeader action
3. **OperatorSubscriptionDetailPage.tsx** — `Subscriptions > {id}` + remove standalone Back button
4. **UserDetailPage.tsx** — `Users > {name}`

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 5: Standardize table row actions

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/005-standardize-table-actions.md` for full details.

Apply consistent row action patterns:
1. **OperatorTenantsPage** — make name a `<Link>`, remove Eye button, use ghost buttons for Edit/Delete
2. **DeviceTable** — ensure device name/ID is a `<Link>`, use ghost buttons for Edit
3. **AlertRulesPage** — change outline buttons to ghost buttons
4. **OtaCampaignsPage** — make name a `<Link>`, simplify row actions

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 6: Fix Alert List controls

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/006-fix-alert-list-controls.md` for full details.

Replace ALL raw `<button>` elements in AlertListPage.tsx with `<Button>` components:
1. Refresh button → `<Button variant="outline" size="sm">`
2. Rules link → `<Button variant="outline" size="sm" asChild><Link to="/alert-rules">Rules</Link></Button>`
3. Tab filters → `<Button variant={active ? "default" : "outline"} size="sm">`
4. Bulk action buttons → `<Button variant="outline" size="sm">`
5. Any custom `<details>` for alert row actions → `<DropdownMenu>`

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 7: Migrate CreateCampaignDialog

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/007-migrate-campaign-dialog.md` for full details.

Replace the custom `<div className="fixed inset-0 z-50">` overlay with Shadcn `<Dialog>`:
1. Replace outer div structure with `<Dialog>` + `<DialogContent>`
2. Add `<DialogHeader>`, `<DialogTitle>`, `<DialogFooter>`
3. Remove custom "X" close button (Dialog has built-in)
4. Change props to `open` + `onOpenChange`
5. Update parent OtaCampaignsPage.tsx to use new prop interface

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 8: Fix confirm dialogs

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/008-fix-confirm-dialogs.md` for full details.

Replace `window.confirm()` / `confirm()` with `<AlertDialog>`:
1. **DashboardBuilder.tsx line 106** — widget removal confirm → AlertDialog with state
2. Any other `confirm()` calls found by grep

Pattern: add `removeTargetId` state, show AlertDialog when non-null, call mutation on confirm.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 9: Build verification

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/009-verify-and-fix.md` for the complete checklist.

1. `cd frontend && npx tsc --noEmit` — must be zero errors
2. `cd frontend && npm run build` — must succeed
3. Functional checks:
   - [ ] Dashboard edit toggle works via gear menu
   - [ ] All pages use PageHeader
   - [ ] All create buttons have Plus icon + "Add {Noun}"
   - [ ] All detail pages have breadcrumbs
   - [ ] All table actions follow the convention
   - [ ] No raw HTML buttons remain
   - [ ] CreateCampaignDialog uses Shadcn Dialog
   - [ ] No window.confirm() calls remain
   - [ ] Dark mode works correctly

---

## Task 10: Update documentation

Open and read `docs/cursor-prompts/phase145-ui-pattern-standardization/010-update-documentation.md` for full details.

Add a **"UI Pattern Conventions"** section to `docs/development/frontend.md` covering:
- Page header action rules
- Table row action rules
- Breadcrumb rules
- Modal/dialog conventions
- Prohibited patterns list
- Update YAML frontmatter: `last-verified` to 2026-02-17, add `145` to `phases` array

Update `docs/index.md` frontmatter: add `145` to `phases` array.

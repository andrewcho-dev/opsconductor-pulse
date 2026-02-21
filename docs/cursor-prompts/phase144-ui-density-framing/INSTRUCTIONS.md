# Phase 144 — Cursor Execution Instructions

Execute these 10 tasks **in order**. Each task depends on the previous one completing successfully. After each task, run `cd frontend && npx tsc --noEmit` to catch errors before moving on.

---

## Task 1: Tighten global spacing

Open and read `docs/cursor-prompts/phase144-ui-density-framing/001-tighten-spacing.md` for full details.

Summary of changes:

1. **AppShell.tsx** — `<main>` padding: `p-6` → `p-4`
2. **card.tsx** — Card: `gap-4` → `gap-2`, `py-4` → `py-3`. CardHeader/Content/Footer: `px-4` → `px-3`, `[.border-b]:pb-4` → `[.border-b]:pb-3`, `[.border-t]:pt-4` → `[.border-t]:pt-3`
3. **All ~47 page files** — `space-y-6` → `space-y-4` on top-level page wrappers in `frontend/src/features/`
4. **Card grid gaps** — `gap-4` → `gap-3` on grid containers holding cards (NOT form layouts)
5. **WidgetContainer.tsx** — CardHeader: `py-2 px-3` → `py-1.5 px-2`. CardContent: `p-2` → `p-1.5`
6. **SubscriptionBanner.tsx** — All three banners: `px-6` → `px-4`
7. **Modal containers** — `p-6 shadow-lg space-y-4` → `p-4 shadow-lg space-y-3`

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 2: Create app footer

Open and read `docs/cursor-prompts/phase144-ui-density-framing/002-app-footer.md` for full details.

1. Create `frontend/src/components/layout/AppFooter.tsx` — a 32px footer bar with version and year
2. Add `<AppFooter />` to AppShell.tsx after `</main>` and before `<Toaster>`
3. Remove version string from AppSidebar.tsx footer (empty the `<SidebarFooter>` to `<SidebarFooter className="p-2" />`), remove unused `packageJson` import

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 3: Viewport containment

Open and read `docs/cursor-prompts/phase144-ui-density-framing/003-viewport-containment.md` for full details.

In `AppShell.tsx`:
1. Outer div: `flex min-h-screen w-full` → `flex h-screen w-full overflow-hidden`
2. Content column div: `flex flex-1 flex-col` → `flex flex-1 flex-col overflow-hidden`

This locks the layout to the viewport. Header and footer stay pinned. Only `<main>` scrolls.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 4: Normalize shapes

Open and read `docs/cursor-prompts/phase144-ui-density-framing/004-normalize-shapes.md` for full details.

1. **badge.tsx** line 8 — `rounded-full` → `rounded-md`
2. **ConnectionStatus.tsx** line 43 — `rounded-full` → `rounded-md`, also `py-1` → `py-0.5`
3. Verify: `rounded-full` should only remain on status dots, switches, radio buttons, stepper circles, progress bars

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 5: Typography hierarchy

Open and read `docs/cursor-prompts/phase144-ui-density-framing/005-typography-hierarchy.md` for full details.

1. **PageHeader.tsx** — `text-xl font-semibold` → `text-lg font-semibold`
2. **CertificateOverviewPage.tsx** — `text-xl font-bold` → `text-lg font-semibold`
3. **OperatorDashboard.tsx:71** — `text-2xl font-semibold` → `text-lg font-semibold`
4. **EmptyState.tsx** — `text-lg font-medium` → `text-sm font-semibold`
5. **font-bold sweep** — change ALL `font-bold` → `font-semibold` except NotFoundPage.tsx and NOCPage.tsx

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 6: KPI number standardization

Open and read `docs/cursor-prompts/phase144-ui-density-framing/006-kpi-number-sweep.md` for full details.

| File | Line | Change |
|------|------|--------|
| SystemMetricsPage.tsx | 171 | `text-5xl font-semibold` → `text-2xl font-semibold` |
| FleetKpiStrip.tsx | 143 | `text-3xl font-bold` → `text-2xl font-semibold` |
| StatCardsWidget.tsx | 33 | `text-3xl font-bold` → `text-2xl font-semibold` |
| KpiTileRenderer.tsx | 108 | `text-3xl font-bold` → `text-2xl font-semibold` |
| DeviceCountRenderer.tsx | 25 | `text-3xl font-bold` → `text-2xl font-semibold` |
| UptimeSummaryWidget.tsx | 15 | `text-3xl font-semibold` → `text-2xl font-semibold` |
| AnalyticsPage.tsx | 382,390,398,406 | `text-2xl font-bold` → `text-2xl font-semibold` |
| OperatorTenantDetailPage.tsx | 155,168,182,195 | `text-2xl font-bold` → `text-2xl font-semibold` |
| SubscriptionInfoCards.tsx | 26 | `text-2xl font-bold` → `text-2xl font-semibold` |
| CertificateOverviewPage.tsx | 155,159,163,167 | `text-2xl font-bold` → `text-2xl font-semibold` |
| FleetHealthWidget.tsx | 92 | `text-2xl font-bold` → `text-2xl font-semibold` |
| HealthScoreRenderer.tsx | 76 | `text-2xl font-bold` → `text-2xl font-semibold` |

**Target:** Zero `text-3xl`, `text-5xl` in features/. Zero `text-2xl font-bold`.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 7: Card title sweep

Open and read `docs/cursor-prompts/phase144-ui-density-framing/007-card-title-sweep.md` for full details.

Remove all `text-lg` and `text-base` overrides from `<CardTitle>` className props. The CardTitle component already defaults to `text-sm font-semibold`.

- 6 files with `text-lg` overrides → remove `text-lg`
- ~12 files with `text-base` overrides → remove `text-base` (keep other classes like `flex items-center gap-2`)

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 8: Empty state padding sweep

Open and read `docs/cursor-prompts/phase144-ui-density-framing/008-empty-state-sweep.md` for full details.

1. **EmptyState.tsx** — `py-12` → `py-8`
2. All `py-20` instances → `py-8`
3. All `py-12` instances in empty/loading states → `py-8`

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 9: Build verification

Open and read `docs/cursor-prompts/phase144-ui-density-framing/009-verify-and-fix.md` for the complete checklist.

1. `cd frontend && npx tsc --noEmit` — must be zero errors
2. `cd frontend && npm run build` — must succeed
3. Visual check:
   - [ ] Tighter spacing — content feels denser, less wasted space
   - [ ] Footer visible at bottom with version string
   - [ ] Header/footer pinned, only content scrolls
   - [ ] Badges are rectangular (rounded-md), not pill-shaped
   - [ ] All KPI numbers are same size (text-2xl)
   - [ ] Card titles are uniform (text-sm)
   - [ ] No font-bold except 404/NOC
   - [ ] Dark mode has no regressions
4. Fix any visual regressions found

---

## Task 10: Update documentation

Open and read `docs/cursor-prompts/phase144-ui-density-framing/010-update-documentation.md` for full details.

Edit `docs/development/frontend.md`:
- Update spacing scale to reflect `p-4`, `space-y-4`, `gap-3`, card `py-3 px-3`
- Add typography hierarchy table
- Update shape rules (badges = rounded-md)
- Add footer documentation
- Add viewport containment notes
- Update YAML frontmatter: `last-verified` to 2026-02-17, add `144` to `phases` array

Edit `docs/index.md`:
- Update YAML frontmatter: `last-verified` to 2026-02-17, add `144` to `phases` array

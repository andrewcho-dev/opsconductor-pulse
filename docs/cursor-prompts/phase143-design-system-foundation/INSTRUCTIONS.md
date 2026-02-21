# Phase 143 — Cursor Execution Instructions

Execute these 9 tasks **in order**. Each task depends on the previous one completing successfully. After each task, run `cd frontend && npx tsc --noEmit` to catch errors before moving on.

---

## Task 1: Update design tokens in `frontend/src/index.css`

Open and read `docs/cursor-prompts/phase143-design-system-foundation/001-design-tokens.md` for full details.

Summary of changes to `frontend/src/index.css`:
1. In `:root`, change `--background: 0 0% 100%` → `--background: 220 14% 96%`
2. In `:root`, change `--sidebar-background: 0 0% 98%` → `--sidebar-background: 220 14% 97%`
3. In `:root`, add status color variables after the chart variables:
   ```css
   --status-online: 122 39% 49%;
   --status-stale: 36 100% 50%;
   --status-offline: 0 0% 62%;
   --status-critical: 4 90% 58%;
   --status-warning: 36 100% 50%;
   --status-info: 210 79% 68%;
   ```
4. In `.dark`, add matching dark-mode status colors:
   ```css
   --status-online: 122 39% 55%;
   --status-stale: 36 80% 55%;
   --status-offline: 0 0% 50%;
   --status-critical: 4 80% 62%;
   --status-warning: 36 80% 55%;
   --status-info: 210 70% 72%;
   ```
5. In the `@theme inline` block, register the status colors as theme colors:
   ```css
   --color-status-online: hsl(var(--status-online));
   --color-status-stale: hsl(var(--status-stale));
   --color-status-offline: hsl(var(--status-offline));
   --color-status-critical: hsl(var(--status-critical));
   --color-status-warning: hsl(var(--status-warning));
   --color-status-info: hsl(var(--status-info));
   ```
6. Replace the hardcoded hex `@utility` blocks with token references AND add bg- and text- variants. Replace the entire utility section with:
   ```css
   @utility status-online { color: hsl(var(--status-online)); }
   @utility status-stale { color: hsl(var(--status-stale)); }
   @utility severity-critical { color: hsl(var(--status-critical)); }
   @utility severity-warning { color: hsl(var(--status-warning)); }
   @utility severity-info { color: hsl(var(--status-info)); }
   @utility text-status-online { color: hsl(var(--status-online)); }
   @utility text-status-stale { color: hsl(var(--status-stale)); }
   @utility text-status-offline { color: hsl(var(--status-offline)); }
   @utility text-status-critical { color: hsl(var(--status-critical)); }
   @utility text-status-warning { color: hsl(var(--status-warning)); }
   @utility text-status-info { color: hsl(var(--status-info)); }
   @utility bg-status-online { background-color: hsl(var(--status-online)); }
   @utility bg-status-stale { background-color: hsl(var(--status-stale)); }
   @utility bg-status-offline { background-color: hsl(var(--status-offline)); }
   @utility bg-status-critical { background-color: hsl(var(--status-critical)); }
   @utility bg-status-warning { background-color: hsl(var(--status-warning)); }
   @utility bg-status-info { background-color: hsl(var(--status-info)); }
   ```

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 2: Update base components

Open and read `docs/cursor-prompts/phase143-design-system-foundation/002-base-components.md` for full details.

### 2a. Edit `frontend/src/components/ui/card.tsx`

| Component | Old className | New className |
|-----------|--------------|---------------|
| Card | `"bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm"` | `"bg-card text-card-foreground flex flex-col gap-4 rounded-lg border py-4"` |
| CardHeader | `"... gap-2 px-6 ... [.border-b]:pb-6"` | `"... gap-1.5 px-4 ... [.border-b]:pb-4"` |
| CardTitle | `"leading-none font-semibold"` | `"text-sm leading-none font-semibold"` |
| CardContent | `"px-6"` | `"px-4"` |
| CardFooter | `"flex items-center px-6 [.border-t]:pt-6"` | `"flex items-center px-4 [.border-t]:pt-4"` |

### 2b. Edit `frontend/src/components/ui/table.tsx`

| Component | Old className | New className |
|-----------|--------------|---------------|
| TableHead | `"text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap ..."` | `"text-foreground h-11 px-3 text-left align-middle font-medium text-xs uppercase tracking-wide text-muted-foreground whitespace-nowrap ..."` |
| TableCell | `"p-2 align-middle whitespace-nowrap ..."` | `"px-3 py-2.5 align-middle whitespace-nowrap ..."` |

### 2c. Edit `frontend/src/components/ui/data-table.tsx`

- Change outer wrapper: `<div className="space-y-4">` → `<div className="space-y-3">`
- Change both table containers (loading state and normal): `<div className="rounded-md border border-border">` → `<div className="rounded-lg border border-border overflow-hidden">`

### 2d. Edit `frontend/src/components/shared/PageHeader.tsx`

- Change h1: `className="text-2xl font-bold"` → `className="text-xl font-semibold"`
- Change breadcrumb nav: `className="mb-1 flex items-center gap-2 text-xs text-muted-foreground"` → `className="mb-1 flex items-center gap-1.5 text-sm text-muted-foreground"`

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 3: Fix AppHeader text sizes

Open and read `docs/cursor-prompts/phase143-design-system-foundation/003-app-shell.md` for full details.

Edit `frontend/src/components/layout/AppHeader.tsx`:

1. Search button: change `text-xs` to `text-sm`:
   ```
   BEFORE: className="hidden sm:flex items-center gap-2 text-muted-foreground text-xs h-8 px-2"
   AFTER:  className="hidden sm:flex items-center gap-2 text-muted-foreground text-sm h-8 px-2"
   ```

2. Keyboard shortcut hint: change `text-[10px]` to `text-xs` (12px is the floor):
   ```
   BEFORE: className="...font-mono text-[10px] font-medium..."
   AFTER:  className="...font-mono text-xs font-medium..."
   ```

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 4: Page spacing sweep

Open and read `docs/cursor-prompts/phase143-design-system-foundation/004-page-spacing-sweep.md` for full details.

**Rule:** Every page component's top-level wrapper must use `space-y-6`. Pages must NOT add their own padding wrapper.

1. Run: `grep -rn 'className="space-y-[^6"]' frontend/src/features/ --include="*.tsx"` to find all non-standard page spacing
2. For each Page.tsx file found, change the top-level wrapper to `space-y-6`
3. Search for double-padding: `grep -rn 'className="p-[3-8]' frontend/src/features/ --include="*.tsx"` — remove any padding wrapper div that sits immediately inside a page component return
4. Normalize grid gaps on card layouts: change `gap-3` and `gap-6` to `gap-4` in card grid containers

**Only change top-level page wrappers.** Inner spacing within cards (space-y-2, space-y-3, space-y-4) is fine and should be left alone.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 5: text-xs sweep

Open and read `docs/cursor-prompts/phase143-design-system-foundation/005-text-xs-sweep.md` for full details.

**Rule:** `text-xs` (12px) is ONLY allowed on timestamps, badges, keyboard hints, chart axis labels. All body content, table cells, form labels, card content must use `text-sm` (14px).

1. Run: `grep -rn "text-xs" frontend/src/features/ --include="*.tsx"` and `grep -rn "text-xs" frontend/src/components/shared/ --include="*.tsx"`
2. For each occurrence, evaluate: is this a timestamp/badge/hint? If yes, keep. If it's body content, table cell text, form label, or card content → change to `text-sm`
3. Focus on high-traffic pages first: dashboard/, devices/, alerts/, operator/, settings/
4. Be thorough — this touches ~99 files

**Target:** Reduce from 434 instances to under 100 (legitimate small-text uses only).

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 6: Border radius sweep

Open and read `docs/cursor-prompts/phase143-design-system-foundation/006-border-radius-sweep.md` for full details.

**Rule:** Cards/containers/modals use `rounded-lg` (8px). Buttons/inputs use `rounded-md` (6px). No `rounded-xl` anywhere.

1. Run: `grep -rn "rounded-xl" frontend/src/ --include="*.tsx" | grep -v node_modules | grep -v card.tsx`
2. Change every `rounded-xl` to `rounded-lg`
3. Run: `grep -rn "rounded-sm" frontend/src/ --include="*.tsx"` — change container uses to `rounded-lg`, small element uses to `rounded-md`

**Target:** Zero `rounded-xl` instances remaining.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 7: Status color token migration

Open and read `docs/cursor-prompts/phase143-design-system-foundation/007-status-color-tokens.md` for full details.

Replace hardcoded Tailwind status colors with token classes throughout `frontend/src/features/`:

| Old | New |
|-----|-----|
| `text-green-500`, `text-green-600` (for online/healthy) | `text-status-online` |
| `bg-green-500`, `bg-green-600` (for online dots) | `bg-status-online` |
| `text-yellow-500`, `text-orange-500`, `text-amber-500` (for stale/warning) | `text-status-warning` or `text-status-stale` |
| `bg-yellow-500`, `bg-orange-500` (for warning dots) | `bg-status-warning` or `bg-status-stale` |
| `text-red-500`, `text-red-600` (for critical/error) | `text-status-critical` |
| `bg-red-500`, `bg-red-600` (for error dots) | `bg-status-critical` |
| `text-gray-400`, `text-gray-500` (for offline) | `text-status-offline` |
| `bg-gray-400` (for offline dots) | `bg-status-offline` |
| `text-blue-400`, `text-blue-500` (for info) | `text-status-info` |

**Only change status/severity colors.** Do NOT change decorative, chart, accent, or primary action colors.

Look for switch/case or ternary patterns that map status strings to colors — fixing these mapping functions fixes many usages at once.

**Checkpoint:** `cd frontend && npx tsc --noEmit && npm run build`

---

## Task 8: Full verification

Open and read `docs/cursor-prompts/phase143-design-system-foundation/008-verify-and-screenshot.md` for the complete checklist.

1. `cd frontend && npx tsc --noEmit` — must be zero errors
2. `cd frontend && npm run build` — must succeed
3. Visual check on each major page:
   - [ ] Page background is light gray (not white) in light mode
   - [ ] Cards are white with no shadow, rounded-lg corners
   - [ ] Consistent space-y-6 between page sections
   - [ ] No body text at 12px (only timestamps/badges)
   - [ ] Page titles are 20px semibold
   - [ ] Table headers are uppercase muted
   - [ ] Status colors work in light and dark mode
   - [ ] Dark mode has no regressions
4. Fix any visual regressions found

---

## Task 9: Update documentation

Open and read `docs/cursor-prompts/phase143-design-system-foundation/009-update-documentation.md` for full details.

Edit `docs/development/frontend.md`:
- Add a "Design System" section documenting the spacing scale, typography hierarchy, border radius rules, background strategy, status color tokens, and 12px minimum text rule
- Update YAML frontmatter: `last-verified` to today, add `143` to `phases` array

Edit `docs/index.md`:
- Update YAML frontmatter: `last-verified` to today, add `143` to `phases` array

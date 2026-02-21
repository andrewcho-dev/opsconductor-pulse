# Task 8: Update Documentation

## Objective

Update project documentation to reflect Phase 175's design system refresh: new color system, sidebar collapse mode, header layout, new components, empty state illustrations, tab conventions, and spacing changes.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/features/device-management.md`
3. `docs/index.md`
4. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `175` to the `phases` array
- Add to `sources`: `frontend/src/index.css`, `frontend/src/components/shared/KpiCard.tsx`, `frontend/src/components/shared/illustrations.tsx`

### Content Changes

#### Update "Design System" section (around line 96)

Add new subsections for the Phase 175 design system changes. Insert after the existing design system content:

```markdown
## Color System (Phase 175)

The application uses a violet/purple primary color (`--primary: 262 83% 58%` in light mode, `262 83% 72%` in dark mode). All semantic tokens (ring, sidebar-primary, chart-1) derive from this primary.

Status colors remain independent of the primary: `--status-online` (green), `--status-stale` (amber), `--status-offline` (gray), `--status-critical` (red).

Color tokens are defined in `frontend/src/index.css` using CSS custom properties consumed by Tailwind v4's `@theme inline` block.

## Sidebar (Phase 175)

The sidebar uses shadcn/ui's `collapsible="icon"` mode:
- Expanded: full-width (16rem) with text labels
- Collapsed: icon-only strip (3rem) with hover tooltips
- Toggle: Cmd+B keyboard shortcut, SidebarTrigger button, or SidebarRail drag edge
- State persists via cookie (`sidebar_state`)

All `SidebarMenuButton` instances must include the `tooltip` prop for accessible icon-mode behavior.

## Header (Phase 175)

The AppHeader renders a compact (h-12) top bar:
- Left: SidebarTrigger + auto-derived breadcrumbs (from URL path)
- Right: Search (Cmd+K) + ConnectionStatus + Notification bell (alert count badge) + User avatar dropdown

The user avatar dropdown contains: Profile, Organization, Theme toggle, and Log out.

Breadcrumbs are no longer rendered by `PageHeader` — they are auto-derived in the header from the URL path.

## Shared Components (Phase 175)

New shared components:
- `components/ui/progress.tsx` — Radix Progress bar (used for quota/usage visualization)
- `components/ui/avatar.tsx` — Radix Avatar with fallback initials
- `components/shared/KpiCard.tsx` — KPI display card: label + big number + optional progress bar + optional description
- `components/shared/illustrations.tsx` — SVG illustration components (IllustrationEmpty, IllustrationSetup, IllustrationError, IllustrationNotFound)

The `EmptyState` component now renders an SVG illustration by default instead of a plain icon.

## Tab Conventions (Phase 175)

- `variant="line"` (underline with primary-colored active indicator): Use for hub page navigation tabs
- `variant="default"` (pill/muted background): Use for filter toggles and small control groups

Hub pages (Alerts, Analytics, Updates, etc.) should use `variant="line"` for their tab navigation.
```

#### Update "Prohibited Patterns" section

Add:
```markdown
- Breadcrumbs in PageHeader (breadcrumbs are auto-derived in the AppHeader from URL)
```

---

## 2. `docs/features/device-management.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `175` to the `phases` array

### Content Changes

No content changes needed — the design system refresh doesn't change device management features. Just the frontmatter update.

---

## 3. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `175` to the `phases` array

### Content Changes

No content changes needed — the design system is documented in `development/frontend.md`.

---

## 4. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `175` to the `phases` array

### Content Changes

No content changes needed — no backend routes changed.

---

## Verification

- All four docs have `last-verified: 2026-02-19` and `175` in their `phases` array
- `docs/development/frontend.md` documents the new color system, sidebar behavior, header layout, shared components, and tab conventions
- No stale information in updated sections

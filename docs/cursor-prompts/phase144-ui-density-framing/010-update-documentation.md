# Task 10: Update Documentation

## Context

Phase 144 tightened spacing, added a footer, normalized shapes, and standardized typography. Update the design system docs.

## Files to Update

### 1. `docs/development/frontend.md`

Update the Design System section with the following changes:

**Spacing scale** — update to:
- AppShell main content: `p-4` (16px)
- Page section spacing: `space-y-4` (16px)
- Card grid gaps: `gap-3` (12px)
- Card internal: `py-3 px-3` with `gap-2`

**Typography hierarchy** — add or update:
- Page title: `text-lg font-semibold` (18px)
- Section heading: `text-sm font-semibold uppercase tracking-wide text-muted-foreground`
- Card title: `text-sm font-semibold` (14px, no overrides allowed)
- KPI number: `text-2xl font-semibold` (24px, universal)
- KPI label: `text-xs text-muted-foreground`
- Body: `text-sm`
- Caption: `text-xs text-muted-foreground`
- Modal title: `text-base font-semibold`
- Weight rule: `font-semibold` only, no `font-bold` (except 404/NOC)

**Shape rules** — update:
- Badges: `rounded-md` (NOT rounded-full)
- `rounded-full` ONLY for: status dots, switches, radio buttons, progress bars
- All other rules unchanged (cards=rounded-lg, buttons/inputs=rounded-md)

**Framing** — add:
- AppFooter: 32px height, border-t, bg-card, shows version + year
- Viewport locked: `h-screen overflow-hidden` on outer container
- Only `<main>` scrolls; header/footer/sidebar are pinned

**Empty states** — add:
- Maximum padding: `py-8`
- Use EmptyState component for consistency

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-17)
- Add `144` to the `phases` array

### 2. `docs/index.md`

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-17)
- Add `144` to the `phases` array

## Verify

```bash
grep "last-verified" docs/development/frontend.md
grep "144" docs/development/frontend.md
```

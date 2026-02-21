# Phase 144 — UI Density, Framing & Visual Consistency

## Goal

Tighten spacing, add a footer for visual framing, normalize shapes (kill pill badges), standardize typography hierarchy, and reduce wasted screen space across the entire frontend.

## Problem Statement

After Phase 143 established design tokens and base rules, the app still suffers from:
1. **Excessive padding** — AppShell `p-6` + page `space-y-6` + card `gap-4 py-4` compounds to ~64px between content blocks
2. **No footer** — content scrolls infinitely with no bottom boundary; the app feels unframed
3. **Pill vs rectangle clash** — Badge component uses `rounded-full` while buttons use `rounded-md`
4. **Random typography** — KPI numbers range from `text-2xl` to `text-5xl`; page titles are smaller than stat numbers
5. **Inconsistent card titles** — ad-hoc overrides of `text-lg`, `text-base` on CardTitle throughout the codebase
6. **Empty states** use `py-20` (80px padding) for placeholder text

## Execution Order

| Task | File | Description |
|------|------|-------------|
| 001 | `001-tighten-spacing.md` | Reduce AppShell, page, card, modal, banner spacing |
| 002 | `002-app-footer.md` | Create AppFooter component and integrate into AppShell |
| 003 | `003-viewport-containment.md` | Lock layout to viewport height with proper scroll zones |
| 004 | `004-normalize-shapes.md` | Badge `rounded-full` → `rounded-md`, ConnectionStatus same |
| 005 | `005-typography-hierarchy.md` | Standardize all text sizes to defined scale |
| 006 | `006-kpi-number-sweep.md` | All KPI/stat numbers → `text-2xl font-semibold` |
| 007 | `007-card-title-sweep.md` | Remove all ad-hoc CardTitle size overrides |
| 008 | `008-empty-state-sweep.md` | Cap empty state padding, standardize EmptyState component |
| 009 | `009-verify-and-fix.md` | Build verification and visual regression fix |
| 010 | `010-update-documentation.md` | Update docs/development/frontend.md |

## Rules

- Run `cd frontend && npx tsc --noEmit` after EVERY task before moving on
- Do NOT change dark mode variables — only light mode spacing/sizing
- Do NOT touch chart colors, chart library code, or ECharts options
- Do NOT change the sidebar width or navigation structure
- KEEP status dot `rounded-full` — only badges/chips change shape
- KEEP switch/radio `rounded-full` — these are semantically circular

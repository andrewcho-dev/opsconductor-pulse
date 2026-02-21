# Phase 143 — Design System Foundation & Consistency Pass

## Goal

Establish a locked design system (tokens, spacing scale, typography hierarchy, background strategy) and sweep all pages/components to conform. This is the foundation layer — a follow-up phase will address deeper layout, viewport containment, and information architecture issues.

## Current State (problems)

- Page background is pure white — cards have no contrast (every major IoT platform uses light gray)
- No spacing scale — ad hoc mix of space-y-3, space-y-4, space-y-6 across 113 files
- Cards use `shadow-sm` + `rounded-xl` — industry standard is borders (no shadow) + `rounded-lg` (8px)
- No heading hierarchy — page titles are `text-2xl font-bold`, card titles have no explicit size
- 434 instances of `text-xs` (12px) — body content is shrunk down everywhere
- Status colors hardcoded in utilities AND scattered as Tailwind classes — not using tokens
- Some pages add extra padding wrappers inside the shell's `p-6` (double-padding)

## Design Decisions (research-backed — see phase143-ui-design-research/)

| Token | Value | Source |
|-------|-------|--------|
| Page bg (light) | `hsl(220, 14%, 96%)` ~#F1F2F6 | AWS Cloudscape, Datadog, Azure |
| Card bg | white `hsl(0, 0%, 100%)` | Universal |
| Inset bg | `hsl(220, 14%, 98%)` | For subtle zones within cards |
| Border radius (cards) | `rounded-lg` (8px) | Fluent 2, majority of SaaS |
| Card containment | 1px border, NO shadow | AWS moved to this, Grafana same |
| Card padding | `p-4` (16px) | Cloudscape "medium" |
| Card-to-card gap | `gap-4` (16px) | Tighter than current gap-6 |
| Page section spacing | `space-y-6` (24px) | Consistent everywhere |
| Body text | 14px (`text-sm`) | Universal across 7 platforms |
| Small text floor | 12px — only for timestamps/badges | AWS mandates 12px minimum |
| Page title (h1) | `text-xl font-semibold` (20px) | Cloudscape h2 / practical for data-dense UI |
| Section title (h2) | `text-base font-semibold` (16px) | Cloudscape h4 |
| Card title (h3) | `text-sm font-semibold` (14px) | Matches body size, weight differentiates |
| Table row height | 44px default | Between Cloudscape 48px and Datadog 36px |

## Execution Order

| Step | File | What | Scope |
|------|------|------|-------|
| 1 | `001-design-tokens.md` | Update CSS variables and base styles in index.css | 1 file |
| 2 | `002-base-components.md` | Update Card, Table, PageHeader, DataTable components | 5 files |
| 3 | `003-app-shell.md` | Fix AppShell main content area and header | 2 files |
| 4 | `004-page-spacing-sweep.md` | Normalize all pages to space-y-6, remove double-padding | ~30 page files |
| 5 | `005-text-xs-sweep.md` | Replace text-xs with text-sm on body content, keep on timestamps/badges only | ~99 files |
| 6 | `006-border-radius-sweep.md` | Normalize rounded-xl → rounded-lg on cards/containers | ~75 files |
| 7 | `007-status-color-tokens.md` | Move all status colors to CSS variables | ~20 files |
| 8 | `008-verify-and-screenshot.md` | Build, type-check, visual verification | validation |
| 9 | `009-update-documentation.md` | Update docs for Phase 143 | 2 files |

## Verification

```bash
# Type check
cd frontend && npx tsc --noEmit

# Build
cd frontend && npm run build

# Visual: load each major page and verify consistent spacing, typography, backgrounds
```

# Phase 175 — Design System Refresh

## Goal

Transform the application's visual identity to match EMQX Cloud Console's level of polish: clean, consistent, spacious, and professional. This phase updates CSS tokens, sidebar behavior, header layout, shared components, and spacing — the foundation for the navigation restructure in Phase 176.

## Execution Order

| # | File | Summary |
|---|------|---------|
| 1 | `001-color-tokens.md` | Update CSS custom properties: new primary color (violet), sidebar tokens, dark theme |
| 2 | `002-sidebar-icon-collapse.md` | Enable icon-only collapse mode, add tooltips, add SidebarRail, style active items |
| 3 | `003-header-refresh.md` | Add notification bell, avatar dropdown, move breadcrumbs to header, clean up layout |
| 4 | `004-new-components.md` | Create Progress, Avatar, and KpiCard components |
| 5 | `005-empty-state-illustrations.md` | Enhance EmptyState with SVG illustrations and bordered container |
| 6 | `006-tab-styling.md` | Update line-variant tabs to use primary color underline, adopt as default for hub pages |
| 7 | `007-spacing-polish.md` | Update PageHeader (remove breadcrumbs), adjust spacing, refine footer, consistency pass |
| 8 | `008-update-docs.md` | Update documentation for Phase 175 |

## Key Design Decisions

- **Primary color**: Violet/purple (`262 83% 58%` light / `262 83% 68%` dark) — inspired by EMQX's `#5E4EFF` but using our own HSL values for the shadcn/ui token system
- **Sidebar**: Changes from `collapsible="offcanvas"` (hides completely) to `collapsible="icon"` (collapses to icon strip) — the EMQX pattern
- **Header**: Becomes the primary horizontal bar with breadcrumbs, search, notifications, and user avatar — like EMQX's top bar
- **Tabs**: `variant="line"` (underline) becomes the standard for hub/content pages; `variant="default"` (pill) reserved for filter/toggle use
- **EmptyState**: Gets SVG illustrations and a bordered container like EMQX's empty states

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Manual checks:
- Primary color is violet/purple throughout (buttons, links, active states, focus rings)
- Sidebar collapses to icon-only mode with tooltips on hover
- Cmd+B toggles sidebar collapse; SidebarRail allows drag-to-toggle
- Header shows: sidebar trigger | breadcrumbs | ... | search | notification bell | avatar
- Notification bell shows alert count badge
- Avatar dropdown contains: profile, org, theme toggle, logout
- KpiCard component renders cleanly (label, number, progress bar)
- EmptyState shows illustrations where used
- Tabs on existing pages use underline style
- Dark mode works correctly with new color system
- All existing functionality preserved

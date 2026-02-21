---
phase: 210
title: Navigation Redesign — EMQX-style Icon Sidebar
goal: Replace current sidebar with a narrow icon-first sidebar that collapses/expands, reorganized into new nav groups
---

# Phase 210 — Navigation Redesign

## Visual Target

EMQX Cloud Console sidebar style:
- Collapsed (default): ~64px wide, icons only, tooltips on hover showing label
- Expanded: ~220px wide, icons + labels
- Expand/contract toggle button at the BOTTOM of the sidebar
- Clean divider separating main nav from support items
- No nested collapsible groups visible in collapsed mode

## New Nav Structure

### Customer sidebar (top section)
| Icon | Label | Route(s) |
|---|---|---|
| Home | Home | /home |
| BarChart2 | Monitoring | /dashboard (default), /alerts |
| BrainCircuit | Intelligence | /analytics (default), /reports |
| Layers | Fleet Management | /devices (default), /rules |
| User | Account | /billing |
| Settings | Settings | /settings |

### Divider

### Customer sidebar (bottom section)
| Icon | Label | Route |
|---|---|---|
| LifeBuoy | Support | /support |

### Operator sidebar (unchanged in structure but restyled to match)
Keep existing operator nav items but apply the same EMQX visual style.

## Execution Order
- 001-sidebar-component.md
- 002-router-support-page.md
- 003-update-docs.md

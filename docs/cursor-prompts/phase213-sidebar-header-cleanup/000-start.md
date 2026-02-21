# Phase 213: Sidebar & Header Cosmetic Cleanup

## Status: COMPLETE (applied 2026-02-21)

## Overview
A set of targeted cosmetic fixes to the left navigation sidebar and top header,
addressing visual noise, redundant controls, and layout defects introduced during
the Phase 210 nav redesign.

## Problems Addressed
1. Alert count badge showing on Alerts nav item (left nav) — redundant with header bell
2. "Collapse" text label next to the sidebar bottom toggle icon — icon-only is sufficient
3. SidebarTrigger button in AppHeader top-left — redundant with sidebar bottom toggle
4. Logo shrinks when sidebar collapses — padding too wide for icon-only rail width
5. Purple left-border accent on active nav item — too heavy; subtle bg is enough
6. Horizontal scrollbar appearing at bottom of left nav
7. Nav structure: Rules lived under Fleet Management — should be its own Automation section

## Execution Order
1. `001-remove-badge-and-collapse-label.md`
2. `002-remove-header-trigger.md`
3. `003-sidebar-layout-fixes.md`
4. `004-automation-nav-section.md`
5. `005-doc-update.md`

## Files Modified
- `frontend/src/components/layout/AppSidebar.tsx`
- `frontend/src/components/layout/AppHeader.tsx`

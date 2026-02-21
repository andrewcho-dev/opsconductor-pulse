# Phase 214: Full-Width Header with Logo + Breadcrumb

## Status: COMPLETE (applied 2026-02-21)

## Overview
Restructure the app shell layout so the top header spans the full viewport width
(including over the sidebar), matching the EMQX Cloud Console pattern where the
header sits above the sidebar/content split rather than beside it.

## Problems Addressed
- AppHeader was inside the sidebar layout flex row — it only spanned the content
  area width, not the full screen width
- No logo in the header — the logo lived in the sidebar's SidebarHeader block
- The sidebar's `position: fixed; top: 0` anchoring caused it to overlap the header,
  hiding the logo and breadcrumb (only right-side actions were visible)

## Architecture
The shadcn `<Sidebar>` component renders its panel as `position: fixed; inset-y: 0`
anchored to the viewport top. When AppHeader is hoisted above SidebarProvider in
the DOM, the sidebar still overlaps the header unless its `top` is explicitly offset.

Fix: pass `className="!top-12 !h-[calc(100svh-3rem)]"` to `<Sidebar>` to push
the fixed panel below the 48px (h-12) header.

## Execution Order
1. `001-appshell-restructure.md`
2. `002-appheader-logo-breadcrumb.md`
3. `003-appheader-separator.md`
4. `004-sidebar-remove-header-block.md`
5. `005-sidebar-top-offset.md`
6. `006-doc-update.md`

## Files Modified
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/AppHeader.tsx`
- `frontend/src/components/layout/AppSidebar.tsx`

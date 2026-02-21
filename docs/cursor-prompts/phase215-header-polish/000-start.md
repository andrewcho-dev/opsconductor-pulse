# Phase 215: Header Polish — Height, Separator, Tab Breadcrumbs

## Overview
Three targeted fixes to the full-width header introduced in Phase 214:
1. Header height is too short compared to the design reference (EMQX Cloud Console)
2. A vertical separator line between the logo and breadcrumbs looks wrong — remove it
3. Tab navigation inside pages does not appear in the breadcrumb trail

## Execution Order
1. `001-header-height.md` — increase h-12 → h-14, update sidebar offset
2. `002-remove-separator.md` — remove Separator element and import
3. `003-tab-breadcrumbs.md` — parse ?tab= query param into breadcrumb trail

## Files Modified
- `frontend/src/components/layout/AppHeader.tsx`
- `frontend/src/components/layout/AppSidebar.tsx`

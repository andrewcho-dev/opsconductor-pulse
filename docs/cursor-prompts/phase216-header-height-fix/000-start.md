# Phase 216: Header Height Fix

## Problem
h-14 (56px) is too short. The target reference (EMQX Cloud Console) uses
a header closer to 64px. The header content (small logo, small text) also
makes 56px look thinner than it is — need both a taller container and
proportionally larger content to fill it.

## Target
h-16 = 64px. Logo bumped from h-7/w-7 (28px) to h-8/w-8 (32px).
Sidebar top offset updated to match exactly.

## Execution Order
1. `001-bump-height.md`

## Files Modified
- `frontend/src/components/layout/AppHeader.tsx`
- `frontend/src/components/layout/AppSidebar.tsx`

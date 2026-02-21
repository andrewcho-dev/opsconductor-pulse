# Phase 148h — Fix Widget Configure/Remove Button Clickability

## Problem

In edit mode, the gear (configure) and X (remove) buttons on widgets cannot be clicked. The drag handle overlay in `DashboardBuilder.tsx` covers the entire top 32px of each widget at `z-10`, blocking all clicks to buttons underneath in the `WidgetContainer` CardHeader.

**Drag handle (DashboardBuilder.tsx:204):**
```tsx
<div className="drag-handle absolute top-0 left-0 right-0 h-8 ... z-10">
```

**Buttons (WidgetContainer.tsx:73):** Inside CardHeader with no z-index — rendered below the drag handle.

## Fix — Single file change

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

### Change 1: Elevate the button container above the drag handle (with title shown)

Line 73, the button container when `showTitle && isEditing`:

Change:
```tsx
<div className="flex gap-1 shrink-0">
```
To:
```tsx
<div className="flex gap-1 shrink-0 relative z-20">
```

Adding `relative z-20` makes these buttons paint above the drag handle's `z-10`.

### Change 2: Elevate the floating buttons above the drag handle (title hidden)

Line 98, the floating button container when `!showTitle && isEditing`:

Change:
```tsx
<div className="absolute top-1 right-1 z-10 flex gap-1">
```
To:
```tsx
<div className="absolute top-1 right-1 z-20 flex gap-1">
```

Bump from `z-10` to `z-20` so these also sit above the drag handle.

## Why This Works

The Card component has `position: relative` but no explicit z-index, so it does NOT create a new stacking context. The buttons with `relative z-20` participate in the same stacking context as the drag handle (`z-10`). Since 20 > 10, the buttons render on top and receive click events.

## Files to Modify

- `frontend/src/features/dashboard/widgets/WidgetContainer.tsx` — 2 class changes (lines 73, 98)

## Verification

1. Enter edit mode on a dashboard with widgets
2. Click the gear icon — config dialog should open
3. Click the X icon — remove confirmation should appear
4. Drag the widget by grabbing anywhere on the top bar EXCEPT the buttons — dragging should still work
5. `cd frontend && npx tsc --noEmit && npm run build` — both pass

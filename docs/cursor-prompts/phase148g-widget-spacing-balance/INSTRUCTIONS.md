# Phase 148g — Balance Widget Internal Spacing

## Problem

Widgets have visibly more whitespace above the content than below it. The spacing is lopsided:

**Current spacing stack (top to bottom):**
- Card `py-0` → 0px (fixed in 148f)
- Card `gap-2` → **8px** gap before CardHeader
- CardHeader `py-1.5` → 6px top + 6px bottom
- Card `gap-2` → **8px** gap between header and content
- CardContent `p-1.5` → 6px padding
- **Total above content: ~28px**

- CardContent `p-1.5` → 6px bottom padding
- Card `py-0` → 0px
- **Total below content: 6px**

The Card component's default `gap-2` (8px between flex children) is applied twice — once above the header and once between header and content. That's 16px of gap the user never asked for.

## Fix — Single file

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

### Change 1: Kill Card's gap and tighten vertical padding

Line 68, change:
```tsx
<Card className="relative h-full flex flex-col overflow-hidden py-0">
```
To:
```tsx
<Card className="relative h-full flex flex-col overflow-hidden py-0 gap-0">
```

Adding `gap-0` overrides the Card's default `gap-2`, eliminating the 16px of inter-element spacing.

### Change 2: Tighten CardHeader padding

Line 70, change:
```tsx
<CardHeader className="flex flex-row items-center justify-between py-1.5 px-2 shrink-0">
```
To:
```tsx
<CardHeader className="flex flex-row items-center justify-between py-1 px-2 shrink-0">
```

Reduce from `py-1.5` (6px) to `py-1` (4px). The title is `text-sm` (14px) — 4px above and below is plenty.

### Change 3: Match content padding to be balanced

Line 119, change:
```tsx
<CardContent className="flex-1 overflow-hidden min-h-0 p-1.5">
```
To:
```tsx
<CardContent className="flex-1 overflow-hidden min-h-0 px-1.5 pt-0 pb-1">
```

- `pt-0`: No top padding on content — the header's bottom padding already provides the gap
- `pb-1`: 4px bottom padding to match the header's top padding, creating visual balance
- `px-1.5`: Keep horizontal padding unchanged

### Result

After these changes:
- **Top:** 4px (header py-1) + header text + 4px (header py-1) = ~22px header block
- **Content top:** 0px gap, 0px padding — content starts immediately after header
- **Content bottom:** 4px padding
- **Bottom:** 0px

The header and content are tight with no wasted gaps. Balanced and consistent.

## Files to Modify

- `frontend/src/features/dashboard/widgets/WidgetContainer.tsx` — 3 class changes on lines 68, 70, 119

## Verification

1. All widgets should have balanced, tight spacing — content fills the card with minimal gaps
2. Title text should have a small uniform margin around it (4px)
3. No visible asymmetry between top and bottom spacing
4. `cd frontend && npx tsc --noEmit && npm run build` — both pass

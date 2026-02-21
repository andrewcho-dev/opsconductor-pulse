# Task 3: Fix AppShell and AppHeader

## Files to Edit

1. `frontend/src/components/layout/AppShell.tsx`
2. `frontend/src/components/layout/AppHeader.tsx`

## Changes

### 1. AppShell — `frontend/src/components/layout/AppShell.tsx`

The main content area currently uses `p-6`. Change to `p-6` stays (24px matches our section spacing), but add a max constraint so content doesn't stretch infinitely on ultra-wide monitors, and ensure the content area is the scroll container (not the page).

**Change the main element:**
```
BEFORE: <main className="flex-1 p-6 overflow-auto">
AFTER:  <main className="flex-1 overflow-auto p-6">
```

This is actually already correct structurally. The key fix is that individual pages must NOT add their own padding wrappers (that's handled in the sweep, Task 4).

No structural changes needed to AppShell — the `p-6` is the correct and only source of page padding.

### 2. AppHeader — `frontend/src/components/layout/AppHeader.tsx`

The header uses `bg-card` which was fine when background was white, but now that the page background is gray, the header should also be white (card color) to create a clean white top bar against the gray page — this is already correct since `bg-card` resolves to white.

**Minor cleanup — remove the `text-xs` from the search button:**
```
BEFORE: className="hidden sm:flex items-center gap-2 text-muted-foreground text-xs h-8 px-2"
AFTER:  className="hidden sm:flex items-center gap-2 text-muted-foreground text-sm h-8 px-2"
```

**Remove the text-[10px] from the keyboard shortcut hint (below 12px minimum):**
```
BEFORE: className="pointer-events-none ml-1 inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground"
AFTER:  className="pointer-events-none ml-1 inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs font-medium text-muted-foreground"
```

`text-xs` (12px) is the floor — no `text-[10px]`.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

Visually: the header should be a clean white bar on top of the gray page background. Search button text should be `text-sm`, keyboard shortcut should be `text-xs` (not 10px).

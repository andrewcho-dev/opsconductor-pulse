# Task 4: Normalize Page Spacing Across All Pages

## Rule

Every page component's top-level wrapper MUST use `space-y-6`. No exceptions.

Pages must NOT add their own padding wrapper (the AppShell's `<main className="flex-1 overflow-auto p-6">` provides the only padding).

## How to Find and Fix

### Step 1: Find all page-level space-y inconsistencies

Search for top-level `space-y-` values in page components:

```bash
grep -rn 'className="space-y-[^6]' frontend/src/features/ --include="*.tsx"
grep -rn "className='space-y-[^6]" frontend/src/features/ --include="*.tsx"
```

### Step 2: Fix each occurrence

For each page component (files ending in `Page.tsx` or page-level components), change the top-level wrapper:

```tsx
// WRONG — inconsistent spacing
<div className="space-y-4">
<div className="space-y-3">

// RIGHT — consistent spacing
<div className="space-y-6">
```

**Important:** Only change the TOP-LEVEL page wrapper. Inner spacing within cards, forms, and sections can legitimately use `space-y-2`, `space-y-3`, or `space-y-4` for tighter internal layouts. The rule is:

- Top-level page wrapper: `space-y-6` (always)
- Inside cards/sections: `space-y-2` to `space-y-4` (context-dependent, leave as-is)

### Step 3: Remove double-padding wrappers

Search for pages that add extra padding inside the shell:

```bash
grep -rn 'className="p-[3-8]' frontend/src/features/ --include="*.tsx" | head -30
```

Look for patterns like:
```tsx
// WRONG — double padding (shell already provides p-6)
return (
  <div className="p-4">
    <div className="space-y-6">
      ...
    </div>
  </div>
);

// RIGHT — no extra wrapper
return (
  <div className="space-y-6">
    ...
  </div>
);
```

Remove any `p-3`, `p-4`, or `p-6` wrapper divs that exist immediately inside a page component's return (the shell already provides padding).

### Known files to fix (from audit)

These pages specifically use non-standard spacing:

| File | Current | Fix |
|------|---------|-----|
| `features/devices/DeviceListPage.tsx` | `space-y-4` | → `space-y-6` |
| `features/devices/DeviceDetailPage.tsx` | `space-y-3` with `p-3` wrapper | → `space-y-6`, remove `p-3` wrapper |
| `features/ota/OtaCampaignsPage.tsx` | `space-y-4` | → `space-y-6` |
| `features/ota/OtaCampaignDetailPage.tsx` | `space-y-6` with `p-4` wrapper | → remove `p-4` wrapper |
| `features/ota/FirmwareListPage.tsx` | `space-y-4` with `p-4` wrapper | → `space-y-6`, remove `p-4` wrapper |

There will be others — the grep will find them all. Fix every one.

### Step 4: Normalize grid gaps

For pages that use CSS grid for card layouts, standardize the gap:

```tsx
// WRONG — various gaps
<div className="grid gap-3 lg:grid-cols-2">
<div className="grid gap-6 lg:grid-cols-2">

// RIGHT — consistent gap-4 for card grids
<div className="grid gap-4 lg:grid-cols-2">
```

Change `gap-3` and `gap-6` in card grid layouts to `gap-4`.

**Exception:** Dashboard widget grids that use react-grid-layout can keep their own gap logic.

## Verification

```bash
# Should return 0 results for page-level wrappers
grep -rn 'className="space-y-[^6]' frontend/src/features/ --include="*.tsx" | grep -i "page"

cd frontend && npx tsc --noEmit
```

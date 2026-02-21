# Task 9: Build Verification and Visual Regression Fix

## Step 1: Type check

```bash
cd frontend && npx tsc --noEmit
```

Fix any TypeScript errors.

## Step 2: Production build

```bash
cd frontend && npm run build
```

Fix any build errors.

## Step 3: Visual verification checklist

Start the dev server and check each major page:

### Spacing
- [ ] Content area has 16px padding (not 24px) — tighter but still breathable
- [ ] Sections separated by 16px (not 24px)
- [ ] Card grids have 12px gaps
- [ ] Cards have 12px internal padding
- [ ] No double-padding patterns (padding inside padding)
- [ ] Modals have 16px padding

### Framing
- [ ] Footer visible at bottom of every page — shows version and year
- [ ] Header stays pinned at top when scrolling
- [ ] Footer stays pinned at bottom when scrolling
- [ ] Only the content area scrolls, not the entire page
- [ ] Sidebar version string is removed (moved to footer)

### Shapes
- [ ] Badges are rectangular with small corner radius (rounded-md), NOT pill-shaped
- [ ] Status indicator dots are still circular (rounded-full)
- [ ] Connection status indicator in header is rectangular (rounded-md)
- [ ] Buttons and badges have matching corner radius

### Typography
- [ ] Page titles are 18px semibold (text-lg)
- [ ] ALL KPI/stat numbers are 24px semibold (text-2xl) — no variation
- [ ] Card titles are uniformly 14px semibold (text-sm)
- [ ] No font-bold anywhere (except 404 page and NOC label)
- [ ] Empty state text is 14px semibold (not 18px)

### Dark mode
- [ ] All changes look correct in dark mode
- [ ] Footer is visible and styled correctly in dark mode
- [ ] No regressions

## Step 4: Fix common issues

### Truncation from tighter padding
If card titles get truncated, add `truncate` class to the title element.

### Layout shifts
If cards in a grid no longer align, ensure all cards in a row have equal min-height via the grid.

### Footer obscuring content
If the footer covers the last bit of scrollable content, ensure `<main>` has proper `overflow-auto` and the outer flex container properly sizes.

## Step 5: Final lint

```bash
cd frontend && npx tsc --noEmit
```

Zero errors before continuing.

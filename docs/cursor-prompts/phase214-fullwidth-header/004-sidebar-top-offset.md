# Task 4: Fix Sidebar Fixed-Position Top Offset

## File
`frontend/src/components/layout/AppSidebar.tsx`

## Root Cause
The shadcn `<Sidebar>` component renders its visible panel as:
  `position: fixed; top: 0; bottom: 0` (`inset-y-0`)

When AppHeader is hoisted above SidebarProvider in the DOM tree, the sidebar's
fixed panel still anchors to `top: 0` (viewport top), overlapping the header.
This hides the logo and breadcrumb — only the right-side header actions remain
visible to the right of the sidebar.

## Fix
Pass overriding Tailwind classes to the `<Sidebar>` component. Because shadcn
applies `className` directly to the fixed panel div, Tailwind's `!` (important)
prefix overrides `inset-y-0`:

```tsx
<Sidebar collapsible="icon" className="!top-12 !h-[calc(100svh-3rem)]">
```

- `!top-12` = `top: 3rem !important` — matches the `h-12` (48px) header height
- `!h-[calc(100svh-3rem)]` — fills the remaining viewport height below the header

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
Confirm clean. Then visually verify in browser:
- Header spans full screen width including over the sidebar area
- Logo is visible at top-left of header
- Breadcrumb appears after the logo separator
- Sidebar starts immediately below the header, not at the top of the viewport

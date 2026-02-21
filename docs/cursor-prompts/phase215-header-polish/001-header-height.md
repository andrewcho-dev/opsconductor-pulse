# Task 1: Increase Header Height

## Files
- `frontend/src/components/layout/AppHeader.tsx`
- `frontend/src/components/layout/AppSidebar.tsx`

## Change 1 — AppHeader.tsx
Increase header height from h-12 (48px) to h-14 (56px).

Find:
```tsx
<header className="flex h-12 items-center gap-2 border-b border-border px-3 bg-card">
```
Replace with:
```tsx
<header className="flex h-14 items-center gap-2 border-b border-border px-4 bg-card">
```
(Also increase horizontal padding from px-3 to px-4 for better breathing room.)

## Change 2 — AppSidebar.tsx
The sidebar's fixed-panel top offset must match the header height exactly.
h-14 = 3.5rem. Update the Sidebar className:

Find:
```tsx
<Sidebar collapsible="icon" className="!top-12 !h-[calc(100svh-3rem)]">
```
Replace with:
```tsx
<Sidebar collapsible="icon" className="!top-14 !h-[calc(100svh-3.5rem)]">
```

## Verification
```bash
cd frontend && npm run build 2>&1 | tail -5
```

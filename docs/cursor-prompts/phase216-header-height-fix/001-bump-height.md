# Task 1: Bump Header to h-16, Update Logo and Sidebar Offset

## File 1 — frontend/src/components/layout/AppHeader.tsx

### Change 1a — Increase header height
Find:
```tsx
<header className="flex h-14 items-center gap-2 border-b border-border px-4 bg-card">
```
Replace with:
```tsx
<header className="flex h-16 items-center gap-2 border-b border-border px-4 bg-card">
```

### Change 1b — Increase logo size to fill the taller header proportionally
Find:
```tsx
          className="h-7 w-7"
```
Replace with:
```tsx
          className="h-8 w-8"
```

---

## File 2 — frontend/src/components/layout/AppSidebar.tsx

### Change 2a — Update sidebar top offset to match h-16 (4rem)
Find:
```tsx
<Sidebar collapsible="icon" className="!top-14 !h-[calc(100svh-3.5rem)]">
```
Replace with:
```tsx
<Sidebar collapsible="icon" className="!top-16 !h-[calc(100svh-4rem)]">
```

---

## After Changes — Build and Deploy

```bash
cd /home/opsconductor/simcloud/frontend && npm run build 2>&1 | tail -5
```

Confirm clean build and report the new asset hash from:
```bash
grep "src=" /home/opsconductor/simcloud/frontend/dist/index.html
```

# Task 3: Sidebar Layout Fixes

## File
`frontend/src/components/layout/AppSidebar.tsx`

## Changes

### 3a — Fix logo shrink on collapse
`SidebarHeader` had `className="p-4"` (16px padding each side). The collapsed
sidebar is ~48px wide (`--sidebar-width-icon`). 16+16=32px of padding leaves
only 16px for the 32px logo — it gets clipped.

Change:
```tsx
<SidebarHeader className="p-4">
```
To:
```tsx
<SidebarHeader className="p-2">
```
8px padding each side leaves the full 32px for the `h-8 w-8` icon.

### 3b — Remove purple left-border on active nav item
In `NavButton`, the active state was applying a left border:
```tsx
className={active ? "border-l-2 border-l-primary" : ""}
```
Remove the custom className entirely. `SidebarMenuButton` already provides a
subtle background highlight via its built-in `isActive` prop styling.

Change to:
```tsx
className=""
```

### 3c — Remove horizontal scrollbar
`SidebarContent` had no overflow constraint, allowing `ml-6` on child items
to cause horizontal overflow.

Change:
```tsx
<SidebarContent>
```
To:
```tsx
<SidebarContent className="overflow-x-hidden">
```

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
Confirm clean build.

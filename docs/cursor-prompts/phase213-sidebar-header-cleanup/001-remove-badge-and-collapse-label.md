# Task 1: Remove Alert Badge and Collapse Text Label

## File
`frontend/src/components/layout/AppSidebar.tsx`

## Changes

### 1a — Remove alert badge from Alerts nav item
The `badge` prop was being passed to the Alerts child nav item showing the open
alert count. This is redundant with the bell icon badge in the top header.

In `NavButton`, the badge render block should remain (other items may use it),
but the Alerts child item must NOT receive a `badge` value. Confirm no `badge`
key is present on `{ label: "Alerts", href: "/alerts", icon: Bell }`.

### 1b — Remove "Collapse" text label from sidebar bottom toggle
In `SidebarFooter`, the collapse/expand button renders a span with "Collapse" or
"Expand" text next to the chevron icon. Remove the span entirely — icon only.

Find and remove:
```tsx
{!isCollapsed && <span>{isCollapsed ? "Expand" : "Collapse"}</span>}
```

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
Confirm clean build.

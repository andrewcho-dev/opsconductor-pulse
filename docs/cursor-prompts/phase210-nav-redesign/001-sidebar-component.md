# Task 1: Redesign AppSidebar.tsx

## File to modify
- `frontend/src/components/layout/AppSidebar.tsx`

## Read first
Read the current `frontend/src/components/layout/AppSidebar.tsx` in full before making any changes.
Also read `frontend/src/app/router.tsx` to understand all existing routes.

## What to build

Redesign the customer sidebar to match EMQX Cloud Console visual style. Keep using the
existing shadcn/ui `Sidebar`, `SidebarProvider`, `SidebarContent`, etc. primitives —
just reorganize and restyle the content.

### Collapsed vs Expanded behavior

The shadcn Sidebar already supports `collapsible="icon"` mode. Use:
```tsx
<Sidebar collapsible="icon">
```

In icon-only mode:
- Show only the icon for each nav item
- Wrap each item in a `<Tooltip>` that shows the label on hover
- The expand toggle at the bottom uses `<SidebarTrigger>` or a custom button

### Nav item structure for customer sidebar

Create a `navItems` array at the top of the component:

```tsx
const mainNavItems = [
  {
    icon: Home,
    label: "Home",
    href: "/home",
    match: ["/home"],
  },
  {
    icon: BarChart2,
    label: "Monitoring",
    href: "/dashboard",
    match: ["/dashboard", "/alerts"],
    children: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Alerts", href: "/alerts", icon: Bell, badge: openAlertCount },
    ],
  },
  {
    icon: BrainCircuit,
    label: "Intelligence",
    href: "/analytics",
    match: ["/analytics", "/reports"],
    children: [
      { label: "Analytics", href: "/analytics", icon: BarChart3 },
      { label: "Reports", href: "/reports", icon: FileText },
    ],
  },
  {
    icon: Layers,
    label: "Fleet Management",
    href: "/devices",
    match: ["/devices", "/rules"],
    children: [
      { label: "Devices", href: "/devices", icon: Cpu },
      { label: "Rules", href: "/rules", icon: Zap },
    ],
  },
  {
    icon: User,
    label: "Account",
    href: "/billing",
    match: ["/billing"],
  },
  {
    icon: Settings,
    label: "Settings",
    href: "/settings",
    match: ["/settings"],
  },
];

const supportNavItems = [
  {
    icon: LifeBuoy,
    label: "Support",
    href: "/support",
    match: ["/support"],
  },
];
```

### Rendering logic

For each nav item:
1. Check if current route matches any path in `match[]` — if so, apply active styling
2. If item has `children` AND sidebar is expanded: render the parent as a collapsible
   section header, children as sub-items below it
3. If item has `children` AND sidebar is collapsed (icon-only): render only the parent
   icon, clicking navigates to `href` (the default child route)
4. If no children: render a simple nav link

### Active item styling (EMQX-inspired)
- Active item: left border accent (2px solid primary color) + slightly highlighted background
- Use `useLocation()` from react-router-dom to determine active state
- Do NOT rely on NavLink's built-in active class — compute it manually from pathname

### Expand toggle at the bottom
Place a `<SidebarTrigger>` (or custom button) at the very bottom of the sidebar,
below the support items. Style it as a small icon button:
- Collapsed: show `ChevronsRight` icon
- Expanded: show `ChevronsLeft` icon
- Add tooltip: "Expand sidebar" / "Collapse sidebar"

### Logo at top
Keep the existing logo/branding at the top. In collapsed mode show only the logo mark
(icon/initials). In expanded mode show full logo + product name.

### Operator sidebar
For the operator role, keep the existing nav groups but apply the same EMQX visual
style (same collapsible behavior, same expand toggle at bottom, same active styling).
Do not change the operator nav items or routes.

### Icons to import from lucide-react
```tsx
import {
  Home, BarChart2, BrainCircuit, Layers, User, Settings, LifeBuoy,
  LayoutDashboard, Bell, BarChart3, FileText, Cpu, Zap,
  ChevronsLeft, ChevronsRight
} from "lucide-react"
```

## After changes
Run: `cd frontend && npm run build 2>&1 | tail -20`
Fix any TypeScript errors before reporting done.

# Task 7: Spacing, Polish, and Consistency Pass

## Objective

Fine-tune spacing, refine the footer, remove the standalone ThemeToggle (moved to avatar dropdown), and ensure visual consistency across the app shell.

## Files to Modify

- `frontend/src/components/layout/AppShell.tsx` — minor spacing
- `frontend/src/components/layout/AppFooter.tsx` — make more subtle
- `frontend/src/components/layout/SubscriptionBanner.tsx` — minor alignment
- `frontend/src/components/shared/PageHeader.tsx` — spacing refinement
- `frontend/src/components/shared/CommandPalette.tsx` — update page list for new nav

## Step 1: AppShell — Content Padding

**File:** `frontend/src/components/layout/AppShell.tsx`

The main content area (line 21) uses `p-4`:
```tsx
<main className="flex-1 overflow-auto p-4">
```

Increase horizontal padding slightly and add a max-width constraint for very wide screens. Change to:
```tsx
<main className="flex-1 overflow-auto px-6 py-4">
```

This gives more horizontal breathing room (matching EMQX's generous content padding).

## Step 2: AppFooter — Subtler

**File:** `frontend/src/components/layout/AppFooter.tsx`

Current footer (lines 3-9) is `h-8` with `bg-card` and `border-t`. Make it more subtle:

```tsx
export function AppFooter() {
  return (
    <footer className="flex h-7 shrink-0 items-center justify-between border-t border-border/50 px-6 text-xs text-muted-foreground/60">
      <span>OpsConductor Pulse v{packageJson.version}</span>
      <span>{new Date().getFullYear()} OpsConductor</span>
    </footer>
  );
}
```

Changes:
- Height reduced: `h-8` → `h-7`
- Border softer: `border-border` → `border-border/50`
- Text more subtle: `text-muted-foreground` → `text-muted-foreground/60`
- Remove `bg-card` (let it inherit the main background)
- Match horizontal padding to content: `px-4` → `px-6`

## Step 3: SubscriptionBanner — Match New Padding

**File:** `frontend/src/components/layout/SubscriptionBanner.tsx`

Update the horizontal padding on all three banner variants to match the new content padding:
- Change `px-4` to `px-6` on all three banner `<div>` elements (lines 51, 79, 115)

## Step 4: PageHeader — Spacing Refinement

**File:** `frontend/src/components/shared/PageHeader.tsx`

Now that breadcrumbs are in the header, the PageHeader is simpler. Add a bottom margin/padding for better separation from content:

```tsx
export function PageHeader({ title, description, action, breadcrumbs }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between pb-2">
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        {description && (
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="flex items-center gap-2">{action}</div>}
    </div>
  );
}
```

Changes from current:
- Added `pb-2` for bottom padding
- Reduced description gap: `mt-1` → `mt-0.5`
- Added `flex items-center gap-2` wrapper for actions (allows multiple action buttons to align)
- Breadcrumbs rendering removed (moved to header in Task 3)

Keep the `breadcrumbs` prop in the interface (for backward compatibility) but don't render it.

## Step 5: CommandPalette — Update Page List

**File:** `frontend/src/components/shared/CommandPalette.tsx`

The `pages` array (lines 138-158) lists pages for search. Update it to reflect the current navigation:

```tsx
const pages = useMemo(
  () => [
    { label: "Home", href: "/", icon: LayoutDashboard },
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Devices", href: "/devices", icon: Cpu },
    { label: "Sites", href: "/sites", icon: Building2 },
    { label: "Templates", href: "/templates", icon: LayoutDashboard },
    { label: "Fleet Map", href: "/map", icon: Layers },
    { label: "Device Groups", href: "/device-groups", icon: Layers },
    { label: "Alerts", href: "/alerts", icon: Bell },
    { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
    { label: "Analytics", href: "/analytics", icon: Gauge },
    { label: "Reports", href: "/reports", icon: ScrollText },
    { label: "OTA Campaigns", href: "/ota/campaigns", icon: Activity },
    { label: "Firmware", href: "/ota/firmware", icon: Activity },
    { label: "Notifications", href: "/notifications", icon: Webhook },
    { label: "Escalation Policies", href: "/escalation-policies", icon: ShieldAlert },
    { label: "On-Call", href: "/oncall", icon: Users },
    { label: "Maintenance Windows", href: "/maintenance-windows", icon: CalendarOff },
    { label: "Delivery Log", href: "/delivery-log", icon: Activity },
    { label: "Subscription", href: "/subscription", icon: CreditCard },
    { label: "Billing", href: "/billing", icon: CreditCard },
    { label: "Profile", href: "/settings/profile", icon: Users },
    { label: "Organization", href: "/settings/organization", icon: Building2 },
    { label: "Users", href: "/users", icon: Users },
    { label: "Roles", href: "/roles", icon: Shield },
    { label: "Getting Started", href: "/fleet/getting-started", icon: Activity },
  ],
  []
);
```

Add any missing icons to the import block. The key additions are: Home, Templates, Fleet Map, OTA Campaigns, Firmware, Billing, Profile, Organization, Getting Started.

## Verification

- `npx tsc --noEmit` passes
- Content area has slightly more horizontal padding (`px-6`)
- Footer is more subtle (lower height, softer text/border)
- Subscription banners match the new padding
- PageHeader is clean without breadcrumbs, action buttons align well
- CommandPalette search finds all major pages
- Overall feel is more spacious and polished

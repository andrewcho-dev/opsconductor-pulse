# Task 9: Build Verification and Regression Fix

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

## Step 3: Functional verification checklist

### Dashboard
- [ ] Settings gear menu contains: Edit Layout, Add Widget (when editing), Rename, Set as Default, Share toggle
- [ ] No standalone "Edit Layout" button in the content area
- [ ] Widgets can still be dragged, resized, configured, and removed in edit mode
- [ ] "Lock Layout" appears in gear menu when editing
- [ ] "Add Your First Widget" still shows on empty dashboard

### Page headers
- [ ] ALL pages use PageHeader component (no custom header layouts)
- [ ] Operator Dashboard uses PageHeader
- [ ] System Dashboard has controls in PageHeader action area
- [ ] Certificate Overview uses PageHeader

### Create buttons
- [ ] All create buttons have Plus icon + "Add {Noun}" format
- [ ] All create buttons are in PageHeader action prop
- [ ] No "+" text prefix (replaced with Plus icon component)
- [ ] No "Create" or "New" verbs (all use "Add")

### Breadcrumbs
- [ ] OTA Campaign Detail has breadcrumbs: OTA Campaigns > {name}
- [ ] Operator Tenant Detail has breadcrumbs: Tenants > {name}
- [ ] Subscription Detail has breadcrumbs: Subscriptions > {id}
- [ ] User Detail has breadcrumbs: Users > {name}
- [ ] No standalone "Back" buttons remain

### Table actions
- [ ] Operator Tenants: name is a Link, Edit/Delete as ghost buttons
- [ ] Alert Rules: Edit/Delete as ghost buttons
- [ ] Channels: MoreHorizontal dropdown (unchanged)
- [ ] Users: MoreHorizontal dropdown (unchanged)
- [ ] OTA Campaigns: name is a Link, simplified actions

### Alert List
- [ ] No raw `<button>` elements — all use Button component
- [ ] Tab-like filters use Button component
- [ ] Refresh and Rules are proper Button components
- [ ] Bulk actions use Button component

### Modals
- [ ] CreateCampaignDialog uses Shadcn Dialog (no custom div overlay)
- [ ] All destructive confirms use AlertDialog (no window.confirm)

### Dark mode
- [ ] All changes look correct in dark mode
- [ ] No regressions

## Step 4: Fix common issues

### Missing imports
If a component errors on `Button`, `Plus`, `MoreHorizontal`, `Link`, `Dialog`, or `AlertDialog`, add the missing import.

### State management after lifting
If dashboard edit state was lifted to DashboardPage, ensure the layout save/flush still works when toggling off edit mode.

### Prop type mismatches
After changing component interfaces (DashboardSettings, DashboardBuilder, CreateCampaignDialog), ensure parent components pass all required props.

## Step 5: Final lint

```bash
cd frontend && npx tsc --noEmit
```

Zero errors before continuing.

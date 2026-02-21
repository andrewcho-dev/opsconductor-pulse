# Phase 177: Settings Hub + Sidebar Refinement

## Overview

This phase consolidates the 4 sidebar Settings items (Notifications, Team, Billing, Integrations) plus Profile and Organization into a single Settings page with its own left-side navigation and subcategories. The main sidebar's Settings section becomes a single "Settings" link.

## Execution Order

1. `001-settings-layout.md` — Create SettingsLayout component with left-side navigation and subcategory labels
2. `002-embedded-props.md` — Add `embedded` prop to OrganizationPage, CarrierIntegrationsPage, BillingPage, ProfilePage, NotificationsHubPage, TeamHubPage
3. `003-sidebar-cleanup.md` — Replace Settings group with single "Settings" link
4. `004-route-updates.md` — Restructure routes under `/settings/`, add redirects from old paths
5. `005-update-docs.md` — Documentation updates

## Design

### Settings Page Layout

The Settings page uses a two-column layout:
- **Left nav** (~200px): links grouped under subcategory labels (Account, Configuration, Access Control, Profile)
- **Right content** (flex-1): renders the active settings section via React Router `<Outlet />`

```
┌──────────────────────────────────────────────────────┐
│ Settings                                              │
│ Manage your organization, integrations, and team      │
│                                                       │
│ ┌─────────────┐ ┌──────────────────────────────────┐ │
│ │ ACCOUNT     │ │                                  │ │
│ │  General    │ │  [Active section content]        │ │
│ │  Billing    │ │                                  │ │
│ │             │ │                                  │ │
│ │ CONFIG      │ │                                  │ │
│ │  Notific.   │ │                                  │ │
│ │  Integr.    │ │                                  │ │
│ │             │ │                                  │ │
│ │ ACCESS      │ │                                  │ │
│ │  Team       │ │                                  │ │
│ │             │ │                                  │ │
│ │ ──────────  │ │                                  │ │
│ │  Profile    │ │                                  │ │
│ └─────────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### URL Structure

All settings routes live under `/settings/`:

| Route | Content | Old Route |
|-------|---------|-----------|
| `/settings` | Redirects to `/settings/general` | — |
| `/settings/general` | Organization settings | `/settings/organization` |
| `/settings/billing` | Billing + subscription | `/billing` |
| `/settings/notifications` | Notifications hub (Channels/Delivery/Dead Letter tabs) | `/notifications` |
| `/settings/integrations` | Carrier integrations | `/settings/carrier` |
| `/settings/access` | Team hub (Members/Roles tabs) | `/team` |
| `/settings/profile` | Personal settings | `/settings/profile` (unchanged) |

### Sidebar: Before → After

**Before:**
```
── SETTINGS ──
  Notifications     /notifications
  Team              /team
  Billing           /billing
  Integrations      /settings/carrier
```

**After:**
```
Settings            /settings
```

4 items → 1 item. Total sidebar: ~12 items.

## Files Modified/Created Summary

| File | Change |
|------|--------|
| `frontend/src/components/layout/SettingsLayout.tsx` | **NEW** — Settings page with left-nav |
| `frontend/src/features/settings/OrganizationPage.tsx` | Add `embedded` prop |
| `frontend/src/features/settings/BillingPage.tsx` | Add `embedded` prop |
| `frontend/src/features/settings/CarrierIntegrationsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/settings/ProfilePage.tsx` | Add `embedded` prop |
| `frontend/src/features/notifications/NotificationsHubPage.tsx` | Add `embedded` prop |
| `frontend/src/features/users/TeamHubPage.tsx` | Add `embedded` prop |
| `frontend/src/components/layout/AppSidebar.tsx` | Replace Settings group with single link |
| `frontend/src/app/router.tsx` | Nest settings routes under SettingsLayout + redirects |
| `frontend/src/components/shared/CommandPalette.tsx` | Update settings page entries |
| `docs/development/frontend.md` | Document SettingsLayout pattern |
| `docs/index.md` | Frontmatter update |
| `docs/services/ui-iot.md` | Note new route structure |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Settings page loads at `/settings` (redirects to `/settings/general`)
- Left-nav shows all 6 sections with subcategory labels
- Each section loads correct content
- Notifications and Team sections show their hub tabs (Channels/Delivery/Dead Letter; Members/Roles)
- Access Control section only visible with `users.read` permission
- Old routes redirect correctly (`/billing` → `/settings/billing`, etc.)
- Sidebar shows single "Settings" link
- Settings link highlights when at any `/settings/*` route

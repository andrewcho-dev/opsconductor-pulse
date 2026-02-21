# Phase 176: Navigation Restructure + Hub Pages + Home Page

## Overview

This phase transforms the customer sidebar from 6 collapsible groups with 24+ items into a flat sidebar with 3 section labels and ~16 items. It creates 5 hub pages that consolidate related standalone pages into tabbed views, adds a new Home landing page, and updates all routes with redirects from old standalone paths.

## Execution Order

Execute these prompts in order — each builds on the previous:

1. `001-home-page.md` — Create Home landing page with fleet KPIs, quick actions, recent alerts
2. `002-alerts-hub.md` — Alerts hub (5 tabs: Inbox, Rules, Escalation, On-Call, Maintenance)
3. `003-analytics-hub.md` — Analytics hub (2 tabs: Explorer, Reports)
4. `004-updates-hub.md` — Updates hub (2 tabs: Campaigns, Firmware)
5. `005-notifications-hub.md` — Notifications hub (3 tabs: Channels, Delivery Log, Dead Letter)
6. `006-team-hub.md` — Team hub (2 tabs: Members, Roles)
7. `007-sidebar-rewrite.md` — Flatten sidebar with 3 section labels, ~16 items
8. `008-route-updates.md` — Update router.tsx with hub routes + redirects
9. `009-update-docs.md` — Documentation updates

## Key Design Decisions

- **Hub page pattern:** Each hub page renders a `PageHeader` + `TabsList variant="line"` + `TabsContent` panels containing existing page components
- **`embedded` prop:** Each existing page gains an optional `embedded?: boolean` prop. When `true`, the page skips its own `PageHeader` and renders action buttons in a simple flex container instead
- **URL-based tab state:** Hub pages use `useSearchParams` to read/write `?tab=value` for deep linking and bookmarkability
- **Flat sidebar:** Customer sidebar uses `SidebarGroupLabel` for section headers (MONITORING, FLEET, SETTINGS) without `Collapsible` wrappers — items are always visible
- **Redirects:** Old standalone routes (e.g., `/alert-rules`, `/ota/campaigns`) redirect to the appropriate hub page with the correct `?tab=` param

## Hub Page Consolidation

| Hub | Route | Tabs | Old Routes Redirected |
|-----|-------|------|-----------------------|
| Alerts | `/alerts` | Inbox, Rules, Escalation, On-Call, Maintenance | `/alert-rules`, `/escalation-policies`, `/oncall`, `/maintenance-windows` |
| Analytics | `/analytics` | Explorer, Reports | `/reports` |
| Updates | `/updates` | Campaigns, Firmware | `/ota/campaigns`, `/ota/firmware` |
| Notifications | `/notifications` | Channels, Delivery Log, Dead Letter | `/delivery-log`, `/dead-letter` |
| Team | `/team` | Members, Roles | `/users`, `/roles` |

## Sidebar: Before vs After

**Before (24+ items, 6 collapsible groups):**
Overview (Dashboard), Fleet (Getting Started, Sites, Templates, Devices, Map, Groups, OTA, Firmware), Monitoring (Alerts, Alert Rules, Escalation, On-Call, Maintenance), Notifications (Channels, Delivery Log, Dead Letter), Analytics (Analytics, Reports), Settings (Profile, Org, Carrier, Subscription, Billing, Team, Roles)

**After (~16 items, flat with 3 section labels):**
Home, **[MONITORING]** Dashboard, Alerts, Analytics, **[FLEET]** Getting Started*, Devices, Sites, Templates, Fleet Map, Device Groups, Updates, **[SETTINGS]** Notifications, Team, Billing, Integrations

(\* = conditional, hidden when dismissed)

## Files Modified/Created Summary

| File | Change |
|------|--------|
| `frontend/src/features/home/HomePage.tsx` | **NEW** — Home landing page |
| `frontend/src/features/alerts/AlertsHubPage.tsx` | **NEW** — Alerts hub |
| `frontend/src/features/analytics/AnalyticsHubPage.tsx` | **NEW** — Analytics hub |
| `frontend/src/features/ota/UpdatesHubPage.tsx` | **NEW** — Updates hub |
| `frontend/src/features/notifications/NotificationsHubPage.tsx` | **NEW** — Notifications hub |
| `frontend/src/features/users/TeamHubPage.tsx` | **NEW** — Team hub |
| `frontend/src/features/alerts/AlertListPage.tsx` | Add `embedded` prop |
| `frontend/src/features/alerts/AlertRulesPage.tsx` | Add `embedded` prop |
| `frontend/src/features/alerts/MaintenanceWindowsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/escalation/EscalationPoliciesPage.tsx` | Add `embedded` prop |
| `frontend/src/features/oncall/OncallSchedulesPage.tsx` | Add `embedded` prop |
| `frontend/src/features/analytics/AnalyticsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/reports/ReportsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/ota/OtaCampaignsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/ota/FirmwareListPage.tsx` | Add `embedded` prop |
| `frontend/src/features/notifications/NotificationChannelsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/delivery/DeliveryLogPage.tsx` | Add `embedded` prop |
| `frontend/src/features/messaging/DeadLetterPage.tsx` | Add `embedded` prop |
| `frontend/src/features/users/UsersPage.tsx` | Add `embedded` prop |
| `frontend/src/features/roles/RolesPage.tsx` | Add `embedded` prop |
| `frontend/src/components/layout/AppSidebar.tsx` | Complete rewrite — flat layout |
| `frontend/src/app/router.tsx` | Hub routes + redirects + Home route |
| `docs/development/frontend.md` | Document hub page pattern |
| `docs/features/device-management.md` | Frontmatter update |
| `docs/index.md` | Add Home page, hub pages to feature list |
| `docs/services/ui-iot.md` | Note new routes |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Home page loads at `/home` with fleet health KPIs
- Each hub page loads and all tabs work
- Tab state persists in URL (`?tab=rules` etc.)
- Old routes redirect correctly to hub pages
- Sidebar shows flat layout with ~16 items
- No broken imports or missing components

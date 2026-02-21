# Task 5: Update Documentation

## Objective

Update project documentation to reflect Phase 180's navigation simplification and Rules hub.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `180` to the `phases` array
- Add to `sources`: `frontend/src/features/rules/RulesHubPage.tsx`

### Content Changes

#### Update "Navigation Structure" section

Replace the current navigation structure with:

```markdown
## Navigation Structure (Phase 180)

The customer sidebar uses a flat layout with 7 items in 2 section labels:

- **Home** — Landing page with fleet health KPIs, quick actions, recent alerts, onboarding checklist
- **Monitoring** — Dashboard, Alerts (inbox only), Analytics (hub)
- **Fleet** — Devices, Rules (hub)
- **Settings** — Single link to `/settings` page with internal subcategory navigation

Fleet management pages not in the sidebar (Sites, Templates, Device Groups, Fleet Map, Updates, Tools) are accessible via a fleet quick-links row on the Devices page, and always findable via the Command Palette (Cmd+K).
```

#### Update "Hub page inventory" table

Update the table:

```markdown
| Hub | Route | Tabs |
|-----|-------|------|
| Rules | `/rules` | Alert Rules, Escalation, On-Call, Maintenance |
| Analytics | `/analytics` | Explorer, Reports |
| Updates | `/updates` | Campaigns, Firmware |
| Notifications | `/settings/notifications` | Channels, Delivery Log, Dead Letter |
| Team | `/settings/access` | Members, Roles |
| Tools | `/fleet/tools` | Connection Guide, MQTT Test Client |
```

Remove the "Alerts" row from the hub inventory (it's no longer a hub — just renders the inbox directly).

#### Add "Devices Fleet Links" note

After the hub page inventory, add:

```markdown
### Devices page fleet links

The Devices page (`/devices`) includes a compact quick-links row below the page header with navigation to fleet management pages not in the sidebar: Sites, Templates, Groups, Map, Updates, Tools. These link to the existing pages at their standard routes.
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `180` to the `phases` array

### Content Changes

Update the feature list entries related to navigation:

Replace:
```markdown
- Hub pages: Alerts, Analytics, Updates, Notifications, Team
- Flat sidebar navigation with section labels
```

With:
```markdown
- Hub pages: Rules, Analytics, Updates, Notifications, Team, Tools
- Minimal sidebar navigation (7 items) with fleet quick-links on the Devices page
```

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `180` to the `phases` array

### Content Changes

Add a new section after "Connection Tools (Phase 178)":

```markdown
## Navigation Simplification (Phase 180)

Phase 180 simplifies the sidebar to 7 items and introduces a Rules hub:

- `/app/rules` — Rules hub with tabs: Alert Rules, Escalation, On-Call, Maintenance
- `/app/alerts` — Simplified to alert inbox only (rules/escalation/oncall/maintenance moved to Rules hub)
- `/app/devices` — Gains a fleet quick-links row for accessing Sites, Templates, Groups, Map, Updates, Tools

Old tab-based URLs (`/alerts?tab=rules`, `/alerts?tab=escalation`, etc.) redirect to the corresponding Rules hub tab.
```

---

## Verification

- All three docs have updated `last-verified` date and `180` in their `phases` array
- `docs/development/frontend.md` reflects the 7-item sidebar and updated hub inventory
- `docs/index.md` mentions the Rules hub and minimal sidebar
- `docs/services/ui-iot.md` documents the new `/rules` route and alerts simplification
- No stale navigation references remain

# Task 5: Update Documentation

## Objective

Update project documentation to reflect Phase 181's tab standardization — all sub-page navigation now uses tabs.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `181` to the `phases` array
- Add to `sources`:
  - `frontend/src/features/devices/DevicesHubPage.tsx`
  - `frontend/src/features/settings/SettingsHubPage.tsx`
- Remove from `sources`: `frontend/src/components/layout/SettingsLayout.tsx` (file deleted)

### Content Changes

#### Update "Navigation Structure" section

Replace the current "Navigation Structure (Phase 180)" section with:

```markdown
## Navigation Structure (Phase 181)

The customer sidebar uses a flat layout with 7 items in 2 section labels:

- **Home** — Landing page with fleet health KPIs, quick actions, recent alerts, onboarding checklist
- **Monitoring** — Dashboard, Alerts (inbox only), Analytics (hub)
- **Fleet** — Devices (hub), Rules (hub)
- **Settings** — Single link to `/settings` hub page

All sub-page navigation uses tabs — there are no left-nav layouts or button-link rows. Every page that contains sub-pages uses the same hub pattern: `PageHeader` + `TabsList variant="line"` + `useSearchParams`.
```

#### Update "Hub page inventory" table

Replace the current hub page inventory table with:

```markdown
| Hub | Route | Tabs |
|-----|-------|------|
| Devices | `/devices` | Devices, Sites, Templates, Groups, Map, Updates, Tools |
| Settings | `/settings` | General, Billing, Notifications, Integrations, Team, Profile |
| Rules | `/rules` | Alert Rules, Escalation, On-Call, Maintenance |
| Analytics | `/analytics` | Explorer, Reports |
| Updates | `/devices?tab=updates` | Campaigns, Firmware (nested, pill variant) |
| Tools | `/devices?tab=tools` | Connection Guide, MQTT Test Client (nested, pill variant) |
| Notifications | `/settings?tab=notifications` | Channels, Delivery Log, Dead Letter (nested, pill variant) |
| Team | `/settings?tab=team` | Members, Roles (nested, pill variant) |
```

#### Remove "Devices page fleet links" section

Delete the "Devices page fleet links" subsection entirely — the quick-links row is replaced by the Devices hub tabs.

#### Replace "Settings Page (Phase 177)" section

Replace the entire "Settings Page (Phase 177)" section with:

```markdown
## Settings Hub (Phase 181)

The Settings page (`/settings`) is a standard hub page with 6 tabs (General, Billing, Notifications, Integrations, Team, Profile). The Team tab is permission-gated — it only renders for users with `users.read` permission.

The old `SettingsLayout` left-nav component has been deleted. All settings navigation uses the same tab pattern as every other hub page.
```

#### Add "Nested Hub Visual Hierarchy" section

After the hub page inventory, add:

```markdown
### Nested hub visual hierarchy

When a hub page is rendered inside another hub's tab (e.g., UpdatesHubPage inside the Devices hub), its internal tabs switch from `variant="line"` to `variant="default"` (pill style). This creates clear visual subordination: outer line tabs → inner pill tabs.

Nested hubs use `useState` (not `useSearchParams`) for inner tab selection when embedded, preventing query param conflicts with the outer hub.
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `181` to the `phases` array

### Content Changes

Replace:
```markdown
- Hub pages: Rules, Analytics, Updates, Notifications, Team, Tools
- Minimal sidebar navigation (7 items) with fleet quick-links on the Devices page
- Settings page with subcategory navigation (Account, Configuration, Access Control)
```

With:
```markdown
- Hub pages: Devices (7 tabs), Settings (6 tabs), Rules, Analytics — all using standardized tab navigation
- Minimal sidebar navigation (7 items) with tab-based sub-page access
```

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `181` to the `phases` array

### Content Changes

#### Update "Settings Route Structure (Phase 177)" section

Replace the entire "Settings Route Structure (Phase 177)" section with:

```markdown
## Settings Hub (Phase 181)

Phase 181 replaces the nested settings routes with a flat hub page:

- `/app/settings` — Settings hub with tabs: General, Billing, Notifications, Integrations, Team, Profile
- `/app/settings?tab=general` — Organization settings (default tab)
- `/app/settings?tab=team` — Team hub (requires `users.read` permission)

Old nested paths (`/app/settings/general`, `/app/settings/billing`, etc.) redirect to the corresponding `?tab=` parameter.
```

#### Add a new section after "Navigation Simplification (Phase 180)"

```markdown
## Tab Standardization (Phase 181)

Phase 181 eliminates all non-tab sub-page navigation patterns (left-nav, button-link rows) and standardizes on tabs:

- `/app/devices` — Devices hub with 7 tabs: Devices, Sites, Templates, Groups, Map, Updates, Tools
- `/app/settings` — Settings hub with 6 tabs: General, Billing, Notifications, Integrations, Team, Profile

Old standalone routes redirect to the appropriate hub tab:
- `/app/sites` → `/app/devices?tab=sites`
- `/app/templates` → `/app/devices?tab=templates`
- `/app/updates` → `/app/devices?tab=updates`
- `/app/settings/general` → `/app/settings?tab=general`
- `/app/settings/access` → `/app/settings?tab=team`

Nested hubs (Updates, Tools inside Devices; Notifications, Team inside Settings) use pill-variant tabs when rendered as inner tabs to create visual hierarchy.
```

#### Update "Navigation & Hub Pages (Phase 176)" section

Update the bullet list to reflect the new hub routes:

Replace:
```markdown
- `/app/alerts` — Alerts hub (rules/escalation/on-call/maintenance are tabs)
- `/app/updates` — Updates hub (replaces `/app/ota/campaigns` and `/app/ota/firmware`)
- `/app/team` — Team hub (replaces `/app/users` and `/app/roles`)
```

With:
```markdown
- `/app/alerts` — Alert inbox (simplified in Phase 180)
- `/app/analytics` — Analytics hub (Explorer, Reports tabs)
- `/app/devices` — Devices hub with 7 tabs (Phase 181)
- `/app/settings` — Settings hub with 6 tabs (Phase 181)
```

---

## Verification

- All three docs have updated `last-verified` date and `181` in their `phases` array
- `docs/development/frontend.md` reflects tab standardization (no mention of left-nav or fleet quick-links as current patterns)
- `docs/development/frontend.md` has updated hub inventory with Devices and Settings hubs
- `docs/development/frontend.md` documents nested hub pill-variant tabs and local state
- `docs/development/frontend.md` no longer references `SettingsLayout.tsx` in sources
- `docs/index.md` mentions Devices and Settings hubs
- `docs/services/ui-iot.md` documents the new `/devices` and `/settings` hub routes with tab parameters
- No stale navigation references remain (no mention of "left-nav", "button links row", or "fleet quick-links" as current patterns)

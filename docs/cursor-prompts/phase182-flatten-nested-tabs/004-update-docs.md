# Task 4: Update Documentation

## Objective

Update project documentation to reflect Phase 182's flattening of nested hub tabs.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `182` to the `phases` array
- Remove from `sources`:
  - `frontend/src/features/fleet/ToolsHubPage.tsx` (deleted)
  - `frontend/src/features/rules/RulesHubPage.tsx` can stay (it still exists)
  - `frontend/src/features/alerts/AlertsHubPage.tsx` can stay
- Add to `sources`:
  - `frontend/src/features/ota/OtaCampaignsPage.tsx`
  - `frontend/src/features/ota/FirmwareListPage.tsx`

### Content Changes

#### Update "Hub page inventory" table

Replace the current table with a flat inventory (no nested entries):

```markdown
| Hub | Route | Tabs |
|-----|-------|------|
| Devices | `/devices` | Devices, Sites, Templates, Groups, Map, Campaigns, Firmware, Guide, MQTT |
| Settings | `/settings` | General, Billing, Channels, Delivery Log, Dead Letter, Integrations, Members, Roles, Profile |
| Rules | `/rules` | Alert Rules, Escalation, On-Call, Maintenance |
| Analytics | `/analytics` | Explorer, Reports |
```

Remove the old nested hub entries (Updates, Tools, Notifications, Team) from the table entirely — they are no longer hubs, just tab content.

#### Remove "Nested hub visual hierarchy" section

Delete the "Nested hub visual hierarchy" subsection entirely — there are no nested hubs anymore.

#### Update "Tab Conventions" section

Replace the current tab conventions with:

```markdown
## Tab Conventions (Phase 182)

- `variant="line"` (underline with primary-colored active indicator): Use for all hub page navigation tabs
- `variant="default"` (pill/muted background): Use for filter toggles and small control groups only

All hubs use a single level of `variant="line"` tabs. There are no nested hubs or pill-variant inner tabs.
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `182` to the `phases` array

### Content Changes

Replace:
```markdown
- Hub pages: Devices (7 tabs), Settings (6 tabs), Rules, Analytics — all using standardized tab navigation
```

With:
```markdown
- Hub pages: Devices (9 tabs), Settings (9 tabs), Rules, Analytics — all flat single-level tab navigation
```

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `182` to the `phases` array

### Content Changes

#### Replace "Tab Standardization (Phase 181)" section

Replace with:

```markdown
## Tab Standardization (Phases 181–182)

All sub-page navigation uses flat single-level tabs. No nested hubs, no left-nav, no button-link rows.

- `/app/devices` — Devices hub with 9 tabs: Devices, Sites, Templates, Groups, Map, Campaigns, Firmware, Guide, MQTT
- `/app/settings` — Settings hub with 9 tabs: General, Billing, Channels, Delivery Log, Dead Letter, Integrations, Members, Roles, Profile

Old standalone routes redirect to the appropriate hub tab:
- `/app/sites` → `/app/devices?tab=sites`
- `/app/templates` → `/app/devices?tab=templates`
- `/app/updates` → `/app/devices?tab=campaigns`
- `/app/ota/firmware` → `/app/devices?tab=firmware`
- `/app/fleet/tools` → `/app/devices?tab=guide`
- `/app/settings/notifications` → `/app/settings?tab=channels`
- `/app/settings/access` → `/app/settings?tab=members`

Members and Roles tabs are permission-gated (`users.read` and `users.roles` respectively).
```

---

## Verification

- All three docs have updated `last-verified` date and `182` in their `phases` array
- `docs/development/frontend.md` hub inventory shows 4 flat hubs (no nested entries)
- `docs/development/frontend.md` has no mention of "nested hub", "pill-variant inner tabs", or "visual hierarchy" for tabs
- `docs/index.md` reflects 9-tab hubs
- `docs/services/ui-iot.md` documents the flat tab structure with correct redirect targets
- No stale references to UpdatesHubPage, ToolsHubPage, NotificationsHubPage, or TeamHubPage as hub pages

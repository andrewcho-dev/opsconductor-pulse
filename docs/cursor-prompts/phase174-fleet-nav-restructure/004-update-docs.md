# Task 4: Update Documentation

## Objective

Update project documentation to reflect Phase 174 changes: fleet navigation restructure, Getting Started page, health strip, and sensor page deprecation.

## Files to Update

1. `docs/features/device-management.md`
2. `docs/development/frontend.md`
3. `docs/index.md`
4. `docs/services/ui-iot.md`

---

## 1. `docs/features/device-management.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `174` to the `phases` array
- Add `frontend/src/features/fleet/GettingStartedPage.tsx` and `frontend/src/components/layout/AppSidebar.tsx` to `sources`

### Content Changes

Add a new section after the "Device Detail UI (Phase 171)" section (after line 87) and before "Telemetry Key Normalization (Phase 172)":

```markdown
## Fleet Navigation & Getting Started (Phase 174)

The Fleet sidebar is organized into workflow-oriented sub-groups:

- **Setup**: Sites, Device Templates, Devices — the fundamental configuration workflow.
- **Monitor**: Fleet Map, Device Groups — observability and logical grouping.
- **Maintain**: OTA Updates, Firmware — ongoing fleet maintenance.

A "Getting Started" page (`/app/fleet/getting-started`) guides new customers through 5 setup steps with live completion detection:

1. Create a site
2. Set up a device template
3. Add your first device
4. Verify data is flowing (device online)
5. Configure alerts

Each step auto-detects completion via API queries. The page is accessible from the Fleet sidebar and auto-dismisses (via localStorage) when dismissed or complete.

The fleet-wide Sensors page is no longer linked in the sidebar (per-device sensors management is now in the Device Detail Sensors & Data tab from Phase 171). The route remains accessible via direct URL with a deprecation tip banner.

The Device List page includes a health summary strip showing online/stale/offline device counts above the device list.
```

---

## 2. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `174` to the `phases` array
- Add `frontend/src/features/fleet/GettingStartedPage.tsx` to `sources`

### Content Changes

In the "Feature Modules" section (around line 56), add `fleet/` to the list of feature areas. Insert alphabetically (between `escalation/` and `map/`):

```markdown
- `fleet/` — fleet-level pages (Getting Started onboarding guide)
```

---

## 3. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `174` to the `phases` array

### Content Changes

In the "Features" section (around line 39), update the Device Management bullet to mention the Getting Started guide:

Change:
```markdown
- [Device Management](features/device-management.md) — Provisioning, templates, modules/sensors/transports, twin, commands, OTA
```

To:
```markdown
- [Device Management](features/device-management.md) — Provisioning, templates, modules/sensors/transports, twin, commands, OTA, Getting Started guide
```

---

## 4. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `174` to the `phases` array
- Add `frontend/src/features/fleet/GettingStartedPage.tsx` to `sources`

### Content Changes

In the "Device Instance Model" section (around line 188), add a note about the new fleet route after the existing content:

```markdown
## Fleet Navigation (Phase 174)

The frontend Fleet sidebar is restructured into Setup / Monitor / Maintain sub-groups. A Getting Started page is served at `/app/fleet/getting-started` with 5-step onboarding and live completion detection. The fleet-wide Sensors page (`/app/sensors`) is removed from sidebar navigation but the route is preserved for backward compatibility.
```

## Verification

- All four docs have `last-verified: 2026-02-19` and `174` in their `phases` array
- No stale information remains in updated sections
- Links and cross-references are valid

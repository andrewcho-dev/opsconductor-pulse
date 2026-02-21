# Task 4: Update Documentation

## Files to Update

1. `docs/development/frontend.md`
2. `docs/services/ui-iot.md`
3. `docs/features/device-management.md`
4. `docs/index.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `186` to the `phases` array

### Content Changes

#### Update Devices hub tab list

Find the line referencing 5 tabs (from Phase 185):
```
| Devices | `/devices` | Devices, Templates, Map, Campaigns, Firmware |
```

Replace with:
```
| Devices | `/devices` | Devices, Templates, Map, Updates |
```

#### Update DataTable usage description

If there's a section on DataTable or device list patterns, update it to note:

```markdown
The device list (`/devices`) uses a full-width `DataTable` with sortable columns (Status, Device ID, Template, Site, Last Seen, Firmware, Alerts), server-side pagination, and row-click navigation to `/devices/:deviceId`. The old master-detail split layout (`DeviceDetailPane`) was removed in Phase 186.
```

---

## 2. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `186` to the `phases` array

### Content Changes

#### Update Devices hub route

Find:
```
- `/app/devices` — Devices hub with 5 tabs: Devices, Templates, Map, Campaigns, Firmware
```

Replace with:
```
- `/app/devices` — Devices hub with 4 tabs: Devices, Templates, Map, Updates
```

#### Update OTA redirect descriptions

Find any references to separate campaigns/firmware tabs and update:
```
- `/app/ota/campaigns` -> `/app/devices?tab=updates`
- `/app/ota/firmware` -> `/app/devices?tab=updates`
- `/app/updates` -> `/app/devices?tab=updates`
```

---

## 3. `docs/features/device-management.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `186` to the `phases` array

### Content Changes

#### Update device list description

If the document describes the device list UI, update to reflect:
- Full-width DataTable with sortable columns replaces old master-detail split
- Row click navigates to device detail page
- Server-side pagination with page size selector
- `DeviceDetailPane` removed — the full `DeviceDetailPage` (6 tabs) is the only detail view

#### Update OTA/Updates section

If there's a section on OTA updates, note that Campaigns and Firmware are now combined under a single "Updates" tab.

---

## 4. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `186` to the `phases` array

### Content Changes

No content changes — Phase 186 is a UI restructure with no new features.

---

## Verification

- All four docs have `186` in their `phases` array
- `last-verified` dates updated to `2026-02-20`
- No stale references to master-detail split, `DeviceDetailPane`, or separate Campaigns/Firmware tabs
- Devices hub described as 4-tab layout
- Device list described as DataTable with row navigation

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
- Add `185` to the `phases` array

### Content Changes

#### Update the Devices Hub tab list

Find the line that lists 9 tabs:
```
| Devices | `/devices` | Devices, Sites, Templates, Groups, Map, Campaigns, Firmware, Guide, MQTT |
```

Replace with:
```
| Devices | `/devices` | Devices, Templates, Map, Campaigns, Firmware |
```

#### Add note about removed tabs

After the Devices hub row in the table, or in the section describing hub pages, add:

```markdown
Sites, Device Groups, Connection Guide, and MQTT Test Client are standalone pages at `/sites`, `/device-groups`, `/fleet/tools`, and `/fleet/mqtt-client` respectively (Phase 185).
```

---

## 2. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `185` to the `phases` array

### Content Changes

#### Update Devices Hub route description

Find:
```
- `/app/devices` — Devices hub with 9 tabs: Devices, Sites, Templates, Groups, Map, Campaigns, Firmware, Guide, MQTT
```

Replace with:
```
- `/app/devices` — Devices hub with 5 tabs: Devices, Templates, Map, Campaigns, Firmware
```

#### Update redirect routes

Find and replace these redirect entries:
```
- `/app/sites` -> `/app/devices?tab=sites`
```
Replace with:
```
- `/app/sites` — Sites overview (standalone page)
```

Find and replace:
```
- `/app/fleet/tools` -> `/app/devices?tab=guide`
```
Replace with:
```
- `/app/fleet/tools` — Connection guide (standalone page)
- `/app/fleet/mqtt-client` — MQTT test client (standalone page)
```

Update or add:
```
- `/app/device-groups` — Device groups management (standalone page)
```

#### Update Connection Guide & MQTT references

Find:
```
- **Connection Guide** (`/app/devices?tab=guide`) — Language-specific code snippets...
- **MQTT Test Client** (`/app/devices?tab=mqtt`) — Browser-based MQTT client...
```

Replace route references:
```
- **Connection Guide** (`/app/fleet/tools`) — Language-specific code snippets...
- **MQTT Test Client** (`/app/fleet/mqtt-client`) — Browser-based MQTT client...
```

---

## 3. `docs/features/device-management.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `185` to the `phases` array

### Content Changes

#### Update Fleet Navigation section

Find the Setup/Monitor/Maintain hierarchy that references the sidebar/tabs. Update to reflect that Sites and Device Groups are standalone pages, not hub tabs:

Replace:
```
- **Setup**: Sites, Device Templates, Devices — the fundamental configuration workflow.
- **Monitor**: Fleet Map, Device Groups — observability and logical grouping.
```

With:
```
- **Setup**: Device Templates, Devices — the fundamental configuration workflow. Sites is a standalone page (`/sites`).
- **Monitor**: Fleet Map — geographic device view. Device Groups is a standalone page (`/device-groups`).
```

---

## 4. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `185` to the `phases` array

### Content Changes

No content changes — Phase 185 is a UI navigation cleanup with no new features.

---

## Verification

- All four docs have `185` in their `phases` array
- `last-verified` dates updated to `2026-02-20`
- No stale references to `?tab=sites`, `?tab=groups`, `?tab=guide`, or `?tab=mqtt`
- Devices Hub described as 5-tab layout
- Standalone routes documented for Sites, Device Groups, Connection Guide, MQTT Test Client

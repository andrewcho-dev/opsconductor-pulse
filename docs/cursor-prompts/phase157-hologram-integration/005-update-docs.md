# Task 5: Update Documentation

## Files to Update

1. **`docs/api/customer-endpoints.md`** — Add the 2 new carrier endpoints (provision, plans)
2. **`docs/services/ui-iot.md`** — Document the carrier sync worker enhancements and provider fixes
3. **`docs/features/device-management.md`** — Add carrier provisioning to device management feature overview

## For Each File

### 1. `docs/api/customer-endpoints.md`

Add a section for the new carrier endpoints under the existing carrier endpoints section:

```markdown
### SIM Provisioning

**`POST /api/v1/customer/devices/{device_id}/carrier/provision`**

Claim a new SIM from the carrier and link it to a device.

- **Permission:** `carrier.links.write`
- **Feature gate:** `carrier_self_service`
- **Body:** `{ carrier_integration_id: int, iccid: string, plan_id?: int }`
- **Response:** `{ provisioned: bool, device_id, carrier_device_id, iccid, claim_result }`

### Plan Discovery

**`GET /api/v1/customer/carrier/integrations/{integration_id}/plans`**

List available data plans from the carrier.

- **Permission:** none (read-only)
- **Response:** `{ plans: [{ id, name, ... }], carrier_name }`
- **Note:** Returns empty array for carriers that don't support plan listing (e.g., 1NCE).
```

Update YAML frontmatter:
- Set `last-verified` to `2026-02-19`
- Add `157` to the `phases` array
- Add `services/ui_iot/routes/carrier.py` to `sources` if not already present

### 2. `docs/services/ui-iot.md`

Add/update a "Carrier Integration" subsection documenting:
- HologramProvider uses query-param auth (`?apikey=...`), not header auth
- Correct Hologram API endpoints for each operation (state changes, usage, SMS)
- The sync worker now updates `sim_status` and `network_status` alongside `data_used_mb`
- Bulk usage optimization via `get_bulk_usage()` (org-level query for Hologram)
- New `claim_sim()` and `list_plans()` provider methods

Update YAML frontmatter:
- Set `last-verified` to `2026-02-19`
- Add `157` to the `phases` array
- Add `services/ui_iot/services/carrier_service.py` and `services/ui_iot/services/carrier_sync.py` to `sources`

### 3. `docs/features/device-management.md`

Add a subsection on SIM provisioning:
- From the device detail page, unlinked devices can now provision a SIM directly
- The provisioning dialog lets users select a carrier integration, enter an ICCID, and optionally pick a data plan
- After provisioning, the device is automatically linked and carrier diagnostics/usage become available

Update YAML frontmatter:
- Set `last-verified` to `2026-02-19`
- Add `157` to the `phases` array
- Add `frontend/src/features/devices/DeviceCarrierPanel.tsx` to `sources`

## General Instructions

For each file:
1. Read the current content first
2. Update the relevant sections to reflect Phase 157 changes
3. Update the YAML frontmatter as specified above
4. Verify no stale information remains (e.g., references to header-based auth for Hologram)
5. If the file doesn't have YAML frontmatter yet, add it

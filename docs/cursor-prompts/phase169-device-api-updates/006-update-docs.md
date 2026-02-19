# Task 6: Update Documentation

## Files to Update

### 1. `docs/api/customer-endpoints.md`

Add or update sections for:
- **Device provisioning** — New `template_id` and `parent_device_id` fields, auto-creation of required sensors
- **Device modules** — Full CRUD at `/devices/{device_id}/modules` with validation rules
- **Device sensors** (restructured) — New per-device endpoints, `source` field semantics, required sensor protection
- **Device transports** — New endpoints replacing `device_connections`, transport_defaults auto-creation
- **Deprecation notices** — Mark legacy `/devices/{device_id}/connection` as deprecated

### 2. `docs/services/ui-iot.md`

Update the routes section to document:
- New module endpoints in `devices.py`
- Updated sensor endpoints in `sensors.py`
- New transport endpoints
- Backward compatibility layer for fleet-wide /sensors

### 3. `docs/features/device-management.md`

Update (or create if it doesn't exist) to explain:
- The template-to-device relationship
- How required sensors are auto-created
- Module assignment flow and validation rules
- Transport configuration model

### For Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 169 changes
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-19`
   - Add `169` to the `phases` array
   - Add `services/ui_iot/routes/devices.py` and `services/ui_iot/routes/sensors.py` to `sources`
4. Verify no stale information remains

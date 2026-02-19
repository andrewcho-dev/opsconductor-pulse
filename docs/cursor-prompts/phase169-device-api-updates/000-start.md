# Phase 169 — Device Instance API Updates

## Goal

Update device CRUD endpoints to use the template model, and add new endpoints for modules, restructured sensors, and transports. This replaces the legacy device_connections and sensors routes with template-aware versions.

## Prerequisites

- Phase 166-168 complete (template tables, instance tables, template API)
- Existing `services/ui_iot/routes/devices.py` and `services/ui_iot/routes/sensors.py`

## Key Design Decisions

1. **Auto-create sensors**: When `template_id` is set on device creation, auto-create `device_sensors` rows for all `is_required=true` template_metrics. Non-required metrics are only created when user explicitly assigns them.
2. **Module validation**: When assigning a module to a slot, validate `slot_key` exists in the device's template. If `compatible_templates` is defined on the slot, validate `module_template_id` is in that array.
3. **Max devices enforcement**: Count existing modules per slot and reject if count would exceed `template_slots.max_devices`.
4. **Backward compatibility**: Keep existing `/api/v1/customer/sensors` fleet-wide endpoint working but have it query from `device_sensors` table.

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-device-crud-updates.md` | Update device create/read to use template_id |
| 2 | `002-module-endpoints.md` | Module assignment CRUD |
| 3 | `003-sensor-endpoints.md` | Restructured sensor endpoints |
| 4 | `004-transport-endpoints.md` | Transport endpoints (replaces connections) |
| 5 | `005-operator-updates.md` | Update operator device endpoints |
| 6 | `006-update-docs.md` | Update API and service docs |

## Verification

```bash
cd services/ui_iot && python -c "
from app import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/api/v1/customer/devices/{device_id}/modules' in str(routes)
assert '/api/v1/customer/devices/{device_id}/transports' in str(routes)
print('All device instance routes registered')
"
```

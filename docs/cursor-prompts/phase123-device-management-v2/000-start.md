# Phase 123: Device Management v2

## Overview

This phase adds four capabilities to the OpsConductor-Pulse IoT platform:

1. **Dynamic Device Groups** -- Query-based groups whose membership is resolved at read time from device state, tags, and site.
2. **Twin Optimistic Concurrency** -- ETag/If-Match version checks on twin desired-state writes to prevent lost updates.
3. **Device Connectivity Log** -- An append-only event log tracking CONNECTED/DISCONNECTED transitions, surfaced in the device detail UI.
4. **Improved Twin Delta** -- A structured diff (added/removed/changed/unchanged) replacing the flat delta map.

## Execution Order

Execute the tasks in numerical order. Each task is self-contained but later tasks may reference schema or APIs from earlier ones.

| Order | File | Summary |
|-------|------|---------|
| 1 | `001-dynamic-device-groups.md` | Migration, API, query resolver, frontend filter builder |
| 2 | `002-twin-versioning.md` | ETag/If-Match on twin writes, 409 handling |
| 3 | `003-device-connectivity-log.md` | Connection events table, evaluator hook, API, timeline UI |
| 4 | `004-improved-twin-delta.md` | Structured delta function, enriched API response, diff UI |

## Key Existing Files

### Backend
- `services/ui_iot/routes/devices.py` -- Device CRUD, twin endpoints (GET /twin, PATCH /twin/desired, GET /twin/delta), device groups, maintenance windows (~1665 lines)
- `services/shared/twin.py` -- `compute_delta(desired, reported)` and `sync_status()` helpers
- `services/ingest_iot/ingest.py` -- MQTT ingest service, shadow endpoints
- `services/evaluator_iot/evaluator.py` -- Alert evaluation loop; upserts device_state with status; detects ONLINE/STALE transitions (returns `previous_status` and `new_status` from RETURNING clause)
- `services/ui_iot/routes/customer.py` -- Base customer routes; imports `tenant_connection`, `get_tenant_id`, `get_db_pool`

### Database
- `db/migrations/061_device_groups.sql` -- Static device_groups + device_group_members tables with RLS
- `db/migrations/076_device_shadow.sql` -- Twin columns on device_state (desired_state, reported_state, desired_version, reported_version, shadow_updated_at)
- `db/migrations/024_device_extended_attributes.sql` -- device_tags table with RLS
- `db/migrations/080_iam_permissions.sql` -- Latest migration (next = 081)

### Frontend
- `frontend/src/features/devices/DeviceGroupsPage.tsx` -- Static groups list/detail with member CRUD
- `frontend/src/features/devices/DeviceTwinPanel.tsx` -- Twin panel (desired editor, reported viewer, delta banner)
- `frontend/src/features/devices/DeviceDetailPage.tsx` -- Device detail layout with panels
- `frontend/src/services/api/devices.ts` -- API client functions (getDeviceTwin, updateDesiredState, fetchDeviceGroups, etc.)
- `frontend/src/services/api/client.ts` -- apiGet, apiPost, apiPatch, apiPut, apiDelete wrappers

## Architecture Patterns

- **RLS**: Every new table must have `ENABLE ROW LEVEL SECURITY` plus a policy using `current_setting('app.tenant_id', true)`.
- **Tenant connection**: Backend uses `async with tenant_connection(pool, tenant_id) as conn:` which sets `app.tenant_id` on the connection.
- **API router**: All customer endpoints use `router = APIRouter(prefix="/customer", ...)` with `JWTBearer()`, `inject_tenant_context`, `require_customer` dependencies.
- **Frontend API**: Functions in `frontend/src/services/api/devices.ts` call the generic `apiGet`/`apiPatch`/etc. wrappers from `client.ts`.

## Verification Strategy

After completing all four tasks, run this integration check:

```bash
# 1. Apply migrations
docker compose exec iot-postgres psql -U iot -d iotcloud -f /migrations/081_dynamic_device_groups.sql
docker compose exec iot-postgres psql -U iot -d iotcloud -f /migrations/082_device_connection_events.sql

# 2. Restart services
docker compose restart ui-iot evaluator-iot ingest-iot

# 3. Run API smoke tests
# Dynamic groups
curl -s -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/customer/device-groups/dynamic \
  -H "Content-Type: application/json" \
  -d '{"name":"Online Devices","query_filter":{"status":"ONLINE"}}' | jq .

# Twin versioning
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/twin | jq '.desired_version'
# Note the ETag header

# Connectivity log
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/connections?limit=10 | jq .

# Structured delta
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/twin/delta | jq '.added, .removed, .changed'

# 4. Frontend
# Open browser to /device-groups, create a dynamic group
# Open browser to /devices/DEVICE-01, check twin panel for version + diff view
# Check Connectivity tab on device detail
```

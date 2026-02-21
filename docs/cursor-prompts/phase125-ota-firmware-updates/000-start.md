# Phase 125 -- OTA Firmware Updates

## Context

OpsConductor Pulse needs to push firmware updates to device fleets. Devices are already
organized into groups (Phase 123: `device_groups`, `device_group_members`). MQTT
command delivery already works (`tenant/{tenant_id}/device/{device_id}/commands`).
The ops_worker service runs background task loops (`worker_loop` in `main.py`).

This phase adds:
1. A firmware version registry and OTA campaign data model (PostgreSQL)
2. API routes for managing firmware versions and OTA campaigns
3. A background worker that rolls out firmware to devices via MQTT at a controlled rate
4. A React UI for creating campaigns, monitoring progress, and managing firmware

## Dependencies

- Phase 123 (Device Management v2) -- device_groups, device_group_members tables
- Existing MQTT infrastructure -- `services/ui_iot/services/mqtt_sender.py` (`publish_alert`)
- ops_worker background task loop -- `services/ops_worker/main.py` (`worker_loop`)
- IoT jobs/commands patterns -- `routes/jobs.py`, `routes/devices.py` (command dispatch)

## Execution Order

| # | File | Scope | Commit message |
|---|------|-------|----------------|
| 1 | `001-ota-data-model-api.md` | DB migrations + API routes | `feat: add OTA firmware versions and campaigns data model and API` |
| 2 | `002-ota-execution-engine.md` | ops_worker campaign rollout + MQTT status ingestion | `feat: add OTA campaign execution engine with MQTT rollout` |
| 3 | `003-ota-ui.md` | React pages, hooks, API service, sidebar + router | `feat: add OTA firmware update UI with campaign management` |

## Key Existing Files

### Backend
- `services/ui_iot/app.py` -- router registration (add `ota_router`)
- `services/ui_iot/routes/customer.py` -- base imports, auth deps, tenant_connection
- `services/ui_iot/routes/jobs.py` -- pattern reference for campaign-style routes
- `services/ui_iot/routes/devices.py` -- pattern reference for MQTT publish, device groups
- `services/ui_iot/services/mqtt_sender.py` -- `publish_alert()` function
- `services/ops_worker/main.py` -- background task loop (`worker_loop`, `asyncio.gather`)
- `services/ops_worker/workers/jobs_worker.py` -- pattern reference for tenant-aware workers
- `services/ops_worker/workers/commands_worker.py` -- pattern reference for expiry workers
- `db/migrations/080_iam_permissions.sql` -- last migration (next = 081)
- `db/migrations/061_device_groups.sql` -- device groups schema reference
- `db/migrations/077_iot_jobs.sql` -- jobs schema/RLS pattern reference

### Frontend
- `frontend/src/app/router.tsx` -- add OTA routes
- `frontend/src/components/layout/AppSidebar.tsx` -- add OTA to Fleet nav group
- `frontend/src/services/api/client.ts` -- `apiGet`, `apiPost`, `apiPatch`, `apiDelete`
- `frontend/src/services/api/jobs.ts` -- pattern reference for API service
- `frontend/src/hooks/use-devices.ts` -- pattern reference for hooks
- `frontend/src/features/jobs/JobsPage.tsx` -- pattern reference for list + detail page

## Verification (after all 3 tasks)

```bash
# 1. Run migrations
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/081_firmware_versions.sql
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/082_ota_campaigns.sql
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/083_ota_device_status.sql

# 2. Verify tables exist
docker exec iot-postgres psql -U iot -d iotcloud -c "\dt firmware_versions"
docker exec iot-postgres psql -U iot -d iotcloud -c "\dt ota_campaigns"
docker exec iot-postgres psql -U iot -d iotcloud -c "\dt ota_device_status"

# 3. Test API (requires auth token)
curl -s http://localhost:8080/customer/firmware | jq .
curl -s -X POST http://localhost:8080/customer/ota/campaigns -d '...' | jq .

# 4. Restart ops_worker and check logs for ota_campaign_worker
docker compose restart ops-worker
docker compose logs ops-worker --tail 50

# 5. Open browser to /app/ota/campaigns -- verify UI loads
# 6. Create a campaign from the UI, start it, observe MQTT messages
```

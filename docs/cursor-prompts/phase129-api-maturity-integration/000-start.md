# Phase 129 -- API Maturity & Integration

## Depends On
- Phase 128 (Simplification completed)

## Goal
Promote the API from ad-hoc route prefixes to a stable, versioned, documented public API surface. Add HMAC webhook signing with retry, and build async data export infrastructure.

## Execution Order

| # | File | Commit message | Risk |
|---|------|---------------|------|
| 1 | `001-api-versioning.md` | `feat: restructure routes to /api/v1/, add backward-compat redirects, remove /api/v2/` | HIGH -- touches every route file and all frontend API calls |
| 2 | `002-openapi-spec.md` | `feat: add OpenAPI metadata, response models, and Swagger UI access control` | MEDIUM -- many endpoint signatures change |
| 3 | `003-webhook-hmac-signing.md` | `feat: add HMAC-SHA256 webhook signing, retry with backoff, delivery audit` | LOW -- isolated to notification senders |
| 4 | `004-data-export-endpoints.md` | `feat: add async data export with background processing and chunked download` | MEDIUM -- new table, new worker, new routes |

## Key Files (by task)

### Task 001 -- API Versioning
**Backend route files (change `prefix=`):**
- `services/ui_iot/routes/customer.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/devices.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/alerts.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/notifications.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/escalation.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/oncall.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/jobs.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/exports.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/metrics.py` -- `/customer` -> `/api/v1/customer`
- `services/ui_iot/routes/roles.py` -- (no prefix currently, add `/api/v1` if applicable)
- `services/ui_iot/routes/users.py` -- (check prefix, update accordingly)
- `services/ui_iot/routes/operator.py` -- `/operator` -> `/api/v1/operator`
- `services/ui_iot/routes/system.py` -- `/operator/system` -> `/api/v1/operator/system`
- `services/ui_iot/routes/api_v2.py` -- DELETE remaining REST endpoints, keep WebSocket at `/api/v2/ws`
- `services/ui_iot/app.py` -- add redirect middleware, remove `api_v2_router` include

**Frontend API client files (update paths):**
- `frontend/src/services/api/alerts.ts`
- `frontend/src/services/api/devices.ts`
- `frontend/src/services/api/notifications.ts`
- `frontend/src/services/api/escalation.ts`
- `frontend/src/services/api/oncall.ts`
- `frontend/src/services/api/jobs.ts`
- `frontend/src/services/api/reports.ts`
- `frontend/src/services/api/metrics.ts`
- `frontend/src/services/api/roles.ts`
- `frontend/src/services/api/users.ts`
- `frontend/src/services/api/operator.ts`
- `frontend/src/services/api/system.ts`
- `frontend/src/services/api/tenants.ts`
- `frontend/src/services/api/subscription.ts`
- `frontend/src/services/api/audit.ts`
- `frontend/src/services/api/delivery.ts`
- `frontend/src/services/api/integrations.ts`
- `frontend/src/services/api/sites.ts`
- `frontend/src/services/api/alert-rules.ts`

### Task 002 -- OpenAPI Spec
- `services/ui_iot/app.py` -- FastAPI constructor metadata, tags_metadata, docs access control
- `services/ui_iot/routes/devices.py` -- response_model, docstrings
- `services/ui_iot/routes/alerts.py` -- response_model, docstrings
- `services/ui_iot/routes/customer.py` -- response_model, docstrings
- `services/ui_iot/routes/notifications.py` -- response_model, docstrings
- `services/ui_iot/routes/exports.py` -- response_model, docstrings
- New file: `services/ui_iot/schemas/responses.py` -- shared Pydantic response models

### Task 003 -- Webhook HMAC Signing
- `services/ui_iot/notifications/senders.py` -- fix send_webhook(), add retry, HMAC
- `services/ui_iot/notifications/dispatcher.py` -- pass audit logger to senders
- `services/ui_iot/routes/notifications.py` -- verify test endpoint uses updated send_webhook

### Task 004 -- Data Export Endpoints
- `services/ui_iot/routes/exports.py` -- new async export endpoints
- `services/ui_iot/schemas/exports.py` -- new Pydantic models for export requests/responses
- `migrations/` -- new `export_jobs` table migration
- `services/ops_worker/workers/export_worker.py` -- new background export processor
- `services/ops_worker/main.py` -- register export worker

## Verification (after all 4 tasks)

```bash
# 1. API versioning -- old paths redirect
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/customer/devices
# Expected: 308

curl -s -o /dev/null -w "%{redirect_url}" http://localhost:8080/customer/devices
# Expected: /api/v1/customer/devices

# 2. New v1 paths work
curl -s http://localhost:8080/api/v1/customer/devices -H "Authorization: Bearer $TOKEN" | jq .total

# 3. /api/v2/ routes are gone (except WebSocket)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v2/devices
# Expected: 404

# 4. OpenAPI spec
curl -s http://localhost:8080/openapi.json | jq .info
curl -s http://localhost:8080/docs  # Swagger UI

# 5. Webhook HMAC
# Set up webhook.site receiver, create a notification channel with secret,
# trigger test notification, verify X-Signature-256 header

# 6. Data export
curl -s -X POST http://localhost:8080/api/v1/customer/exports \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"export_type":"devices","format":"csv"}' | jq .export_id
# Poll status, download when COMPLETED
```

## Architecture Notes

- Frontend API client (`frontend/src/services/api/client.ts`) uses relative paths (no baseURL). Each API module (e.g., `alerts.ts`) hardcodes paths like `/customer/alerts`. These all need `/api/v1` prefix.
- Route files use `from routes.customer import *` pattern -- the customer.py router prefix change propagates, but each route file defines its OWN `router = APIRouter(prefix="/customer", ...)`, so each file needs its prefix changed independently.
- The `roles.py` router has `tags=["roles"]` but NO explicit prefix -- check if it registers routes under a prefix or not. If not, add `/api/v1` prefix.
- The `api_v2.py` WebSocket endpoint is `@ws_router.websocket("/api/v2/ws")` on a SEPARATE router (`ws_router`) with no prefix. This should remain as-is or be moved to `/api/v1/customer/ws`.
- The deprecation middleware in `app.py` references `/customer/integrations` -- update to `/api/v1/customer/integrations`.
- CSRF exempt paths in `app.py` need updating if any `/customer/` paths are checked.

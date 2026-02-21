# Phase 130 -- Message Routing & Event Export

## Depends On

- Phase 129 (API Maturity) -- HMAC webhook signing, API versioning, pagination patterns.

## Overview

This phase adds three capabilities to OpsConductor-Pulse:

1. **Message Routing Rules** -- Customers configure rules that match incoming MQTT telemetry by topic pattern and payload filters, then fan out to external destinations (webhooks, MQTT republish, or the default PostgreSQL write).
2. **Dead Letter Queue (DLQ)** -- When a routed delivery fails (webhook timeout, connection refused, etc.), the message lands in a dead_letter_messages table. Customers can inspect, replay, or discard failed messages via API and a new frontend page.
3. **Streaming Telemetry Export** -- Real-time WebSocket and Server-Sent Events (SSE) endpoints that forward live MQTT telemetry to authenticated clients with per-device/group/metric filtering.

## Execution Order

| Step | File | Commit message |
|------|------|----------------|
| 1 | `001-message-routing-rules.md` | `feat(phase130): add message routing rules table, API, and ingest fan-out` |
| 2 | `002-dead-letter-queue.md` | `feat(phase130): add dead letter queue with replay, purge, and operator UI` |
| 3 | `003-streaming-telemetry-export.md` | `feat(phase130): add WebSocket and SSE streaming telemetry export endpoints` |

Each task = 1 commit. Complete each task fully before moving to the next.

## Key Existing Files

| File | Role |
|------|------|
| `services/ingest_iot/ingest.py` | MQTT ingest worker -- subscribes to `tenant/+/device/+/+`, validates, writes to TimescaleDB via batch writer. The `db_worker` method (line ~957) is the integration point for message routing fan-out. |
| `services/ui_iot/routes/notifications.py` | Notification channels & routing rules CRUD (existing alert-level routing). Pattern to follow for new route files. |
| `services/ui_iot/routes/customer.py` | Customer API router, prefix `/customer`. Houses most tenant-scoped endpoints. |
| `services/ui_iot/routes/api_v2.py` | API v2 router with existing WebSocket endpoint at `/api/v2/ws`. Has `setup_ws_listener()` and `_ws_push_loop()` patterns. |
| `services/ui_iot/ws_manager.py` | WebSocket connection manager (`WSConnection` dataclass, `ConnectionManager` class). |
| `services/ui_iot/app.py` | FastAPI app -- router registration happens here (line ~171). New routers must be imported and included. |
| `services/ui_iot/db/pool.py` | `tenant_connection()` context manager for RLS-scoped DB access. |
| `services/ui_iot/dependencies.py` | `get_db_pool` dependency, `pagination()` helper. |
| `services/ui_iot/notifications/senders.py` | `send_webhook()` function with HMAC signing -- reuse for message route webhook delivery. |
| `services/ui_iot/middleware/auth.py` | `JWTBearer()` dependency, `validate_token()` function. |
| `services/ui_iot/middleware/tenant.py` | `inject_tenant_context`, `require_customer`, `get_tenant_id`, `get_user`. |
| `db/migrations/004_enable_rls.sql` | RLS pattern: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation_policy`. |
| `db/migrations/068_notification_channels.sql` | Migration pattern for notification tables with RLS. |
| `db/migrations/077_iot_jobs.sql` | Recent migration pattern with RLS policies. |
| `frontend/src/app/router.tsx` | React router -- add new routes here for DLQ page. |
| `frontend/src/features/delivery/DeliveryLogPage.tsx` | Similar page pattern for the DLQ frontend (table + filters + actions). |

## Database Roles & RLS Pattern

All new tables must follow this exact pattern:

```sql
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON {table_name}
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

Existing roles: `pulse_app` (RLS-scoped), `pulse_operator` (BYPASSRLS), `iot` (login user, granted both roles).

Grant permissions on new tables:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON {table_name} TO pulse_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON {table_name} TO pulse_operator;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_operator;
```

## API Pattern

All customer-facing routes use the standard dependency chain:

```python
router = APIRouter(
    prefix="/customer",
    tags=["message-routing"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)
```

Use `tenant_connection(pool, tenant_id)` for all DB access. Use `get_tenant_id()` to extract the tenant from middleware context.

## Migration Numbering

The highest existing migration is `080_iam_permissions.sql`. New migrations for this phase:

- `081_message_routes.sql`
- `082_dead_letter_messages.sql`

## Verification (All Tasks)

After completing all three tasks, run the following integration test sequence:

```bash
# 1. Create a message route (webhook type)
curl -X POST http://localhost:8080/customer/message-routes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Forward high-temp readings",
    "topic_filter": "tenant/+/device/+/telemetry",
    "destination_type": "webhook",
    "destination_config": {"url": "https://httpbin.org/post", "method": "POST"},
    "payload_filter": {"temperature": {"$gt": 80}},
    "is_enabled": true
  }'

# 2. Send telemetry that matches the route
mosquitto_pub -h localhost -p 1883 -t "tenant/TENANT1/device/DEV-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:00Z","site_id":"SITE-1","provision_token":"...","metrics":{"temperature":90}}'

# 3. Verify webhook was called (check httpbin.org response or use webhook.site)

# 4. Break the webhook URL, send telemetry again, verify DLQ entry
curl http://localhost:8080/customer/dead-letter \
  -H "Authorization: Bearer $TOKEN"

# 5. Fix URL, replay from DLQ
curl -X POST http://localhost:8080/customer/dead-letter/{id}/replay \
  -H "Authorization: Bearer $TOKEN"

# 6. Connect streaming WebSocket
websocat ws://localhost:8080/api/v1/customer/telemetry/stream?token=$TOKEN

# 7. Send telemetry, see it appear in WebSocket stream
```

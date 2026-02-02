# Task 005: Test Delivery Endpoint

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Customers create webhook integrations but need to verify they work before relying on them for alerts. A test delivery endpoint sends a sample payload to the webhook URL and returns the result synchronously.

**Read first**:
- `services/ui_iot/routes/customer.py` (integration routes)
- `services/webhook_dispatcher/app.py` (existing delivery logic, for reference)
- `services/ui_iot/db/queries.py`

**Depends on**: Tasks 003, 004

## Task

### 5.1 Create test payload generator

Add to `services/ui_iot/routes/customer.py` or create utility module:

**Function**: `generate_test_payload(tenant_id: str, integration_name: str) -> dict`

Returns a sample alert payload:
```json
{
  "_test": true,
  "_generated_at": "2026-02-02T12:00:00Z",
  "alert_id": "test-00000000-0000-0000-0000-000000000000",
  "tenant_id": "tenant-a",
  "device_id": "TEST-DEVICE-001",
  "site_id": "TEST-SITE",
  "alert_type": "STALE_DEVICE",
  "severity": "WARNING",
  "summary": "Test alert from OpsConductor Pulse",
  "message": "This is a test delivery to verify your webhook integration is working correctly.",
  "integration_name": "My Webhook",
  "created_at": "2026-02-02T12:00:00Z"
}
```

The `_test: true` field clearly marks this as a test payload.

### 5.2 Add test delivery route

**Route**: `POST /customer/integrations/{integration_id}/test`

**Logic**:
1. Get tenant_id from context
2. Fetch integration by (tenant_id, integration_id)
3. If not found: return 404
4. Generate test payload
5. Extract webhook URL from integration config
6. Perform HTTP POST to webhook URL:
   - Timeout: 10 seconds
   - Headers: `Content-Type: application/json`
   - Body: test payload as JSON
7. Capture result:
   - `success`: bool (2xx response)
   - `http_status`: int or null
   - `latency_ms`: int
   - `error`: string or null
8. Return result

**Response format**:
```json
{
  "success": true,
  "http_status": 200,
  "latency_ms": 145,
  "error": null,
  "payload_sent": { ... }
}
```

Or on failure:
```json
{
  "success": false,
  "http_status": null,
  "latency_ms": 10000,
  "error": "Connection timeout",
  "payload_sent": { ... }
}
```

### 5.3 Error handling

Map common errors to user-friendly messages:

| Error Type | Message |
|------------|---------|
| Connection timeout | "Connection timeout after 10 seconds" |
| DNS failure | "Could not resolve hostname" |
| Connection refused | "Connection refused by server" |
| SSL error | "SSL certificate verification failed" |
| Non-2xx response | "Server returned HTTP {status}" |

### 5.4 Rate limiting

Prevent abuse of test endpoint:

**Limit**: 5 test deliveries per minute per tenant

**Implementation**: Database-backed counter (required for multi-worker deployments)

Add to `services/ui_iot/db/queries.py`:

```
async def check_and_increment_rate_limit(conn, tenant_id: str, action: str, limit: int, window_seconds: int) -> tuple[bool, int]
```
- Query: Count rows in rate_limit table WHERE tenant_id=$1 AND action=$2 AND created_at > now() - interval
- If count >= limit: return (False, count)
- Else: INSERT new row, return (True, count + 1)

**Rate limit table** (add migration if needed):
```sql
CREATE TABLE IF NOT EXISTS rate_limits (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX rate_limits_lookup_idx ON rate_limits(tenant_id, action, created_at DESC);
```

**Cleanup strategy (clean on check)**:
- On each rate limit check, delete expired rows for the current tenant+action
- Add to `check_and_increment_rate_limit`:
  ```sql
  DELETE FROM rate_limits
  WHERE tenant_id = $1 AND action = $2 AND created_at < now() - interval '$3 seconds'
  ```
- Run this BEFORE counting, so stale rows don't accumulate
- This keeps the table small without requiring a separate cleanup job

**On rate limit exceeded**: Return 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Maximum 5 test deliveries per minute."
}
```

**Note**: In-memory counters are NOT acceptable as they don't work across multiple workers/containers.

### 5.5 Logging

Log test delivery attempts for debugging (do NOT store in delivery_attempts table):

```python
logger.info(
    "Test delivery",
    tenant_id=tenant_id,
    integration_id=integration_id,
    success=result["success"],
    latency_ms=result["latency_ms"]
)
```

### 5.6 Role check

Only `customer_admin` can trigger test deliveries. Apply `require_customer_admin` dependency.

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/003_rate_limits.sql` |
| MODIFY | `services/ui_iot/db/queries.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |

**Migration file `003_rate_limits.sql`**:
```sql
-- Migration: 003_rate_limits.sql
-- Purpose: Rate limiting table for test delivery and other endpoints
-- Date: 2026-02-02

CREATE TABLE IF NOT EXISTS rate_limits (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS rate_limits_lookup_idx
    ON rate_limits(tenant_id, action, created_at DESC);

COMMENT ON TABLE rate_limits IS 'Rate limiting entries for tenant-scoped actions';
```

## Acceptance Criteria

- [ ] Migration `003_rate_limits.sql` runs without errors
- [ ] `rate_limits` table exists with index
- [ ] `POST /customer/integrations/{id}/test` sends test payload
- [ ] Test payload includes `_test: true` marker
- [ ] Response includes success, http_status, latency_ms
- [ ] Timeout after 10 seconds with appropriate error
- [ ] DNS/connection errors return user-friendly messages
- [ ] Rate limiting enforced (5/minute/tenant) across multiple workers
- [ ] `customer_viewer` gets 403
- [ ] Test deliveries NOT stored in delivery_attempts table

**Test scenario**:
```
1. Login as customer1 (tenant-a)
2. Create integration with URL: https://webhook.site/{unique-id}
3. POST /customer/integrations/{id}/test
4. Confirm 200 response with success=true
5. Check webhook.site - confirm test payload received
6. Confirm _test=true in received payload
7. Rapidly send 6 test requests
8. Confirm 6th request returns 429
```

## Commit

```
Add test delivery endpoint for webhook integrations

- POST /customer/integrations/{id}/test triggers test delivery
- Sample payload with _test=true marker
- Returns success, http_status, latency_ms
- Database-backed rate limiting (5/minute/tenant)
- Migration 003_rate_limits.sql for rate limit table
- User-friendly error messages for connection failures

Part of Phase 2: Customer Integration Management
```

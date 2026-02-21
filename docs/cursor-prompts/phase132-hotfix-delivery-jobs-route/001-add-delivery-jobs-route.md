# 001 -- Add /delivery-jobs Route Backed by notification_jobs

## Context

The frontend `DeliveryLogPage` (`frontend/src/features/delivery/DeliveryLogPage.tsx`) and its API client (`frontend/src/services/api/delivery.ts`) call:

1. `GET /api/v1/customer/delivery-jobs?status=X&limit=N&offset=N` expecting:
```json
{
  "jobs": [
    {
      "job_id": 1,
      "alert_id": 42,
      "integration_id": "ch-5",
      "route_id": "rule-3",
      "status": "COMPLETED",
      "attempts": 2,
      "last_error": null,
      "deliver_on_event": "OPEN",
      "created_at": "2026-02-16T00:00:00Z",
      "updated_at": "2026-02-16T00:01:00Z"
    }
  ],
  "total": 100
}
```

2. `GET /api/v1/customer/delivery-jobs/{jobId}/attempts` expecting:
```json
{
  "job_id": 1,
  "attempts": [
    {
      "attempt_no": 1,
      "ok": true,
      "http_status": 200,
      "latency_ms": 120,
      "error": null,
      "started_at": "2026-02-16T00:00:00Z",
      "finished_at": "2026-02-16T00:00:01Z"
    }
  ]
}
```

The underlying data lives in two tables:

### `notification_jobs` (migration 070)
```
job_id BIGSERIAL PK
tenant_id TEXT
alert_id BIGINT
channel_id INTEGER (FK notification_channels)
rule_id INTEGER (FK notification_routing_rules)
deliver_on_event TEXT
status TEXT (PENDING/PROCESSING/COMPLETED/FAILED)
attempts INTEGER
next_run_at TIMESTAMPTZ
last_error TEXT
payload_json JSONB
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### `notification_log` (migration 068, extended in 070)
```
log_id BIGSERIAL PK
channel_id INTEGER
alert_id INTEGER
sent_at TIMESTAMPTZ
job_id BIGINT (FK, added in 070)
success BOOLEAN (added in 070)
error_msg TEXT (added in 070)
```

Note: `notification_log` does NOT have `http_status`, `latency_ms`, or a numbered `attempt_no`. The attempts endpoint will need to synthesize these from available data.

## Task

### Step 1: Add two endpoints to `services/ui_iot/routes/exports.py`

Add these after the existing `delivery_status` route (line 42):

#### Endpoint 1: `GET /delivery-jobs`

```python
@router.get("/delivery-jobs")
async def list_delivery_jobs(
    status: str | None = Query(None),
    integration_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
```

Logic:
- Get `tenant_id` from `get_tenant_id()`
- Build a dynamic query against `notification_jobs` with optional `status` and `channel_id` (mapped from `integration_id` parameter) filters
- Run TWO queries in one connection: a COUNT(*) for total and a SELECT with LIMIT/OFFSET for the page
- Map response fields: `channel_id` → `integration_id` (cast to string), `rule_id` → `route_id` (cast to string or null)
- Return `{"jobs": [...], "total": N}`

SQL for the data query:
```sql
SELECT job_id, alert_id, channel_id, rule_id, status, attempts,
       last_error, deliver_on_event, created_at, updated_at
FROM notification_jobs
WHERE tenant_id = $1
  [AND status = $2]
  [AND channel_id = $3]
ORDER BY created_at DESC
LIMIT $N OFFSET $M
```

SQL for the count query:
```sql
SELECT COUNT(*) FROM notification_jobs
WHERE tenant_id = $1 [AND status = $2] [AND channel_id = $3]
```

Map each row to the frontend shape:
```python
{
    "job_id": row["job_id"],
    "alert_id": row["alert_id"],
    "integration_id": str(row["channel_id"]),
    "route_id": str(row["rule_id"]) if row["rule_id"] else None,
    "status": row["status"],
    "attempts": row["attempts"],
    "last_error": row["last_error"],
    "deliver_on_event": row["deliver_on_event"],
    "created_at": row["created_at"].isoformat() + "Z" if row["created_at"] else None,
    "updated_at": row["updated_at"].isoformat() + "Z" if row["updated_at"] else None,
}
```

#### Endpoint 2: `GET /delivery-jobs/{job_id}/attempts`

```python
@router.get("/delivery-jobs/{job_id}/attempts")
async def get_delivery_job_attempts(
    job_id: int,
    pool=Depends(get_db_pool),
):
```

Logic:
- Get `tenant_id` from `get_tenant_id()`
- First verify the job belongs to this tenant: `SELECT 1 FROM notification_jobs WHERE job_id = $1 AND tenant_id = $2`
- If not found, return 404
- Query `notification_log` for all entries matching this `job_id`:
```sql
SELECT log_id, success, error_msg, sent_at
FROM notification_log
WHERE job_id = $1
ORDER BY sent_at ASC
```
- Map each row to the frontend shape, synthesizing missing fields:
```python
{
    "attempt_no": idx + 1,  # enumerate from 1
    "ok": row["success"] if row["success"] is not None else True,
    "http_status": 200 if row["success"] else 500,  # synthesized
    "latency_ms": None,  # not tracked in notification_log
    "error": row["error_msg"],
    "started_at": row["sent_at"].isoformat() + "Z" if row["sent_at"] else None,
    "finished_at": row["sent_at"].isoformat() + "Z" if row["sent_at"] else None,  # same as started (best available)
}
```
- Return `{"job_id": job_id, "attempts": [...]}`

### Step 2: Add necessary imports at top of `exports.py`

The file already imports `Query`, `Depends`, `get_db_pool`, `tenant_connection`, `get_tenant_id`, `HTTPException`, and `logger` via the `from routes.customer import *` wildcard. Verify these are available; if not, add explicit imports.

### Step 3: Verify

No migration needed — we're querying existing tables.

```bash
# 1. Rebuild backend
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. Test delivery-jobs endpoint (should return 200 with jobs array)
curl -s http://localhost:8080/api/v1/customer/delivery-jobs?limit=10 \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. Test delivery-jobs with status filter
curl -s "http://localhost:8080/api/v1/customer/delivery-jobs?status=FAILED&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. If there are jobs, test attempts endpoint
curl -s http://localhost:8080/api/v1/customer/delivery-jobs/1/attempts \
  -H "Authorization: Bearer $TOKEN" | jq .

# 5. Verify DeliveryLogPage loads without 404 in browser
```

## Commit

```
fix: add /delivery-jobs route backed by notification_jobs table

The DeliveryLogPage frontend calls /api/v1/customer/delivery-jobs but
no backend route existed. The old delivery_jobs table was dropped in
migration 071 when the notification pipeline was consolidated. Add
routes that query the replacement notification_jobs and notification_log
tables, mapping responses to the shape the frontend expects.
```

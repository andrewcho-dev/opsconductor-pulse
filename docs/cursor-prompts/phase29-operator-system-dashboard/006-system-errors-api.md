# Phase 29.6: System Errors API

## Task

Create `/operator/system/errors` endpoint that returns recent system errors, failures, and notable events.

---

## Add Errors Endpoint

**File:** `services/ui_iot/routes/system.py`

Add to the existing system router:

```python
from fastapi import Query

@router.get("/errors")
async def get_system_errors(
    request: Request,
    hours: int = Query(1, ge=1, le=24, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=200, description="Max errors to return"),
):
    """
    Get recent system errors and failures.
    Aggregates from various error sources across the platform.
    """
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        # Delivery failures
        delivery_failures = await conn.fetch(
            """
            SELECT
                'delivery' as source,
                'delivery_failed' as error_type,
                created_at as timestamp,
                tenant_id,
                jsonb_build_object(
                    'job_id', id,
                    'integration_id', integration_id,
                    'attempts', attempt_count,
                    'last_error', last_error
                ) as details
            FROM delivery_jobs
            WHERE status = 'FAILED'
              AND created_at >= now() - make_interval(hours := $1)
            ORDER BY created_at DESC
            LIMIT $2
            """,
            hours,
            limit,
        )

        # Quarantined messages (if table exists)
        quarantine_events = []
        try:
            quarantine_events = await conn.fetch(
                """
                SELECT
                    'ingest' as source,
                    'quarantined' as error_type,
                    created_at as timestamp,
                    tenant_id,
                    jsonb_build_object(
                        'device_id', device_id,
                        'reason', reason,
                        'topic', topic
                    ) as details
                FROM quarantine
                WHERE created_at >= now() - make_interval(hours := $1)
                ORDER BY created_at DESC
                LIMIT $2
                """,
                hours,
                limit,
            )
        except Exception:
            # Table might not exist
            pass

        # Authentication failures from operator audit log
        auth_failures = await conn.fetch(
            """
            SELECT
                'auth' as source,
                'auth_failure' as error_type,
                timestamp,
                tenant_id,
                jsonb_build_object(
                    'user_id', user_id,
                    'action', action,
                    'ip_address', ip_address
                ) as details
            FROM operator_audit_log
            WHERE action LIKE '%fail%' OR action LIKE '%denied%'
              AND timestamp >= now() - make_interval(hours := $1)
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            hours,
            limit,
        )

        # Rate limit events (if tracked)
        rate_limit_events = []
        try:
            rate_limit_events = await conn.fetch(
                """
                SELECT
                    'ingest' as source,
                    'rate_limited' as error_type,
                    created_at as timestamp,
                    tenant_id,
                    jsonb_build_object(
                        'device_id', device_id,
                        'count', event_count
                    ) as details
                FROM rate_limit_events
                WHERE created_at >= now() - make_interval(hours := $1)
                ORDER BY created_at DESC
                LIMIT $2
                """,
                hours,
                limit,
            )
        except Exception:
            # Table might not exist
            pass

        # Error counts by type
        error_counts = await conn.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM delivery_jobs
                 WHERE status = 'FAILED'
                   AND created_at >= now() - make_interval(hours := $1)) AS delivery_failures,

                (SELECT COUNT(*) FROM quarantine
                 WHERE created_at >= now() - make_interval(hours := $1)) AS quarantined,

                (SELECT COUNT(*) FROM delivery_jobs
                 WHERE status = 'PENDING'
                   AND created_at < now() - interval '5 minutes') AS stuck_deliveries
            """,
            hours,
        )

    # Combine and sort all errors
    all_errors = []

    for row in delivery_failures:
        all_errors.append({
            "source": row["source"],
            "error_type": row["error_type"],
            "timestamp": row["timestamp"].isoformat() + "Z",
            "tenant_id": row["tenant_id"],
            "details": dict(row["details"]) if row["details"] else {},
        })

    for row in quarantine_events:
        all_errors.append({
            "source": row["source"],
            "error_type": row["error_type"],
            "timestamp": row["timestamp"].isoformat() + "Z",
            "tenant_id": row["tenant_id"],
            "details": dict(row["details"]) if row["details"] else {},
        })

    for row in auth_failures:
        all_errors.append({
            "source": row["source"],
            "error_type": row["error_type"],
            "timestamp": row["timestamp"].isoformat() + "Z",
            "tenant_id": row["tenant_id"],
            "details": dict(row["details"]) if row["details"] else {},
        })

    for row in rate_limit_events:
        all_errors.append({
            "source": row["source"],
            "error_type": row["error_type"],
            "timestamp": row["timestamp"].isoformat() + "Z",
            "tenant_id": row["tenant_id"],
            "details": dict(row["details"]) if row["details"] else {},
        })

    # Sort by timestamp descending
    all_errors.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "errors": all_errors[:limit],
        "counts": {
            "delivery_failures": error_counts["delivery_failures"] or 0,
            "quarantined": error_counts["quarantined"] or 0,
            "stuck_deliveries": error_counts["stuck_deliveries"] or 0,
        },
        "period_hours": hours,
    }
```

---

## Add Rate Limit Tracking Table (Optional)

If you want to track rate limit events:

**File:** `db/migrations/020_rate_limit_events.sql`

```sql
-- Track rate limit events for operator visibility
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    event_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_rate_limit_events_created ON rate_limit_events(created_at);
CREATE INDEX idx_rate_limit_events_tenant ON rate_limit_events(tenant_id);

-- Auto-cleanup old events (keep 24 hours)
-- Run periodically: DELETE FROM rate_limit_events WHERE created_at < now() - interval '24 hours';
```

---

## Verification

```bash
# Restart UI
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Test errors endpoint
curl -H "Authorization: Bearer <token>" "http://localhost:8080/operator/system/errors?hours=24&limit=20"
```

Expected response:
```json
{
  "errors": [
    {
      "source": "delivery",
      "error_type": "delivery_failed",
      "timestamp": "2024-01-15T10:02:15Z",
      "tenant_id": "acme",
      "details": {
        "job_id": 12345,
        "integration_id": 5,
        "attempts": 5,
        "last_error": "Connection timeout"
      }
    },
    {
      "source": "ingest",
      "error_type": "quarantined",
      "timestamp": "2024-01-15T10:01:45Z",
      "tenant_id": "acme",
      "details": {
        "device_id": "dev-042",
        "reason": "Invalid JSON",
        "topic": "tenant/acme/device/dev-042/telemetry"
      }
    }
  ],
  "counts": {
    "delivery_failures": 12,
    "quarantined": 7,
    "stuck_deliveries": 2
  },
  "period_hours": 24
}
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/system.py` |
| CREATE | `db/migrations/020_rate_limit_events.sql` (optional) |

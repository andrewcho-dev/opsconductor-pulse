# Prompt 001 — Backend: GET /customer/devices/{device_id}/telemetry/history

Read `services/ui_iot/routes/customer.py` — find device endpoints.
Read `db/migrations/021_telemetry_hypertable.sql` to confirm exact column names.
Read `services/evaluator_iot/evaluator.py` — find `check_duration_window()` to understand existing telemetry queries.

## Add Endpoint

```python
from typing import Literal

VALID_RANGES = {
    "1h":  ("1 hour",  "1 minute"),
    "6h":  ("6 hours", "5 minutes"),
    "24h": ("24 hours","15 minutes"),
    "7d":  ("7 days",  "1 hour"),
    "30d": ("30 days", "6 hours"),
}

@router.get("/devices/{device_id}/telemetry/history", dependencies=[Depends(require_customer)])
async def get_telemetry_history(
    device_id: str,
    metric: str = Query(...),                    # e.g. "temperature"
    range: str = Query("24h"),                   # 1h|6h|24h|7d|30d
    pool=Depends(get_db_pool)
):
    if range not in VALID_RANGES:
        raise HTTPException(status_code=400, detail=f"Invalid range. Must be one of: {list(VALID_RANGES)}")
    tenant_id = get_tenant_id()
    lookback, bucket = VALID_RANGES[range]

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                time_bucket($1::interval, time)           AS bucket,
                AVG((metrics->>$2)::numeric)              AS avg_val,
                MIN((metrics->>$2)::numeric)              AS min_val,
                MAX((metrics->>$2)::numeric)              AS max_val,
                COUNT(*)                                   AS sample_count
            FROM telemetry
            WHERE tenant_id = $3
              AND device_id = $4
              AND time > now() - $5::interval
              AND metrics ? $2
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            bucket, metric, tenant_id, device_id, lookback
        )

    return {
        "device_id": device_id,
        "metric": metric,
        "range": range,
        "bucket_size": bucket,
        "points": [
            {
                "time": r["bucket"].isoformat(),
                "avg": float(r["avg_val"]) if r["avg_val"] is not None else None,
                "min": float(r["min_val"]) if r["min_val"] is not None else None,
                "max": float(r["max_val"]) if r["max_val"] is not None else None,
                "count": r["sample_count"],
            }
            for r in rows
        ],
    }
```

## Acceptance Criteria

- [ ] GET /customer/devices/{id}/telemetry/history exists
- [ ] `?metric=temperature&range=24h` returns time-bucketed points
- [ ] Returns `avg`, `min`, `max`, `count` per bucket
- [ ] 400 on invalid range value
- [ ] Empty result (no data) returns `points: []`
- [ ] `pytest -m unit -v` passes

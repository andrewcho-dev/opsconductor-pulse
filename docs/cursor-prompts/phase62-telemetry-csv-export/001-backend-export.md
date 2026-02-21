# Prompt 001 — Backend: GET /customer/devices/{id}/telemetry/export

Read `services/ui_iot/routes/customer.py` — find `get_telemetry_history` (~line 693) to understand the range/query pattern.

## Add Export Endpoint

```python
import csv
import io
from fastapi.responses import StreamingResponse

EXPORT_RANGES = {
    "1h":  "1 hour",
    "6h":  "6 hours",
    "24h": "24 hours",
    "7d":  "7 days",
    "30d": "30 days",
}

@router.get("/devices/{device_id}/telemetry/export", dependencies=[Depends(require_customer)])
async def export_telemetry_csv(
    device_id: str,
    range: str = Query("24h"),
    limit: int = Query(5000, ge=1, le=10000),
    pool=Depends(get_db_pool),
):
    if range not in EXPORT_RANGES:
        raise HTTPException(status_code=400, detail=f"Invalid range. Must be one of: {list(EXPORT_RANGES)}")
    tenant_id = get_tenant_id()
    lookback = EXPORT_RANGES[range]

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT time, device_id, site_id, seq, metrics
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND time > now() - $3::interval
            ORDER BY time ASC
            LIMIT $4
            """,
            tenant_id, device_id, lookback, limit
        )

    if not rows:
        # Return empty CSV with headers only
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["time", "device_id", "site_id", "seq"])
        output.seek(0)
        filename = f"{device_id}_telemetry_{range}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # Collect all metric keys across all rows to build unified column headers
    all_metric_keys = sorted({key for row in rows for key in (row["metrics"] or {}).keys()})
    headers = ["time", "device_id", "site_id", "seq"] + all_metric_keys

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        metrics = row["metrics"] or {}
        writer.writerow([
            row["time"].isoformat(),
            row["device_id"],
            row["site_id"] or "",
            row["seq"],
            *[metrics.get(k, "") for k in all_metric_keys],
        ])

    output.seek(0)
    filename = f"{device_id}_telemetry_{range}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

## Acceptance Criteria

- [ ] GET /customer/devices/{id}/telemetry/export exists
- [ ] Returns `Content-Type: text/csv`
- [ ] `Content-Disposition: attachment; filename=...` header set
- [ ] Each metric key in JSONB becomes a column
- [ ] Empty data returns CSV with headers only (not 404)
- [ ] 400 on invalid range
- [ ] Limit capped at 10000 rows
- [ ] `pytest -m unit -v` passes

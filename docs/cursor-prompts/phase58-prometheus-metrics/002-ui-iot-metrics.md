# Prompt 002 — ui_iot /metrics Endpoint

Read `services/ui_iot/app.py` and `services/ui_iot/routes/customer.py`.
Read `services/shared/metrics.py` (just written).

## Add /metrics Route

In `services/ui_iot/app.py` (or a new `routes/metrics.py`):

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint(pool=Depends(get_db_pool)):
    """
    Prometheus metrics endpoint. No auth — intended for internal scraping only.
    Queries DB for current fleet state and updates gauges before rendering.
    """
    from shared.metrics import fleet_active_alerts, fleet_devices_by_status

    # Query current alert counts per tenant
    async with pool.acquire() as conn:
        alert_rows = await conn.fetch(
            """
            SELECT tenant_id, COUNT(*) AS cnt
            FROM fleet_alert
            WHERE status IN ('OPEN', 'ACKNOWLEDGED')
            GROUP BY tenant_id
            """
        )
        device_rows = await conn.fetch(
            """
            SELECT tenant_id, status, COUNT(*) AS cnt
            FROM device
            GROUP BY tenant_id, status
            """
        )

    for row in alert_rows:
        fleet_active_alerts.labels(tenant_id=row["tenant_id"]).set(row["cnt"])

    for row in device_rows:
        fleet_devices_by_status.labels(
            tenant_id=row["tenant_id"], status=row["status"]
        ).set(row["cnt"])

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

Note: The pool.acquire() here uses the operator-level connection (BYPASSRLS) since this is a system endpoint, not a tenant-scoped request. Confirm that `get_db_pool` provides this. If ui_iot has a separate operator pool, use that.

## Acceptance Criteria

- [ ] GET /metrics returns Prometheus text format (Content-Type: text/plain; version=0.0.4)
- [ ] Contains `pulse_fleet_active_alerts` gauge
- [ ] Contains `pulse_fleet_devices_by_status` gauge
- [ ] No auth required
- [ ] `pytest -m unit -v` passes

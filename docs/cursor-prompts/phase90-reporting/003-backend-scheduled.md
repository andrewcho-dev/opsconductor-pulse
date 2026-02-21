# Phase 90 — Backend: SLA Report + Scheduled Worker

## New file: `services/ui_iot/reports/sla_report.py`

```python
async def generate_sla_report(pool, tenant_id: str, days: int = 30) -> dict:
    """
    Returns a dict:
    {
      "period_days": 30,
      "total_devices": N,
      "online_devices": N,
      "online_pct": 94.2,
      "total_alerts": N,
      "unresolved_alerts": N,
      "mttr_minutes": 45.3,   # mean time to resolve (CLOSED alerts only)
      "top_alerting_devices": [{"device_id": "...", "count": N}, ...]
    }
    """
```

### Queries (run inside `tenant_connection(pool, tenant_id)`):

```sql
-- Device counts
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE status = 'ONLINE') AS online
FROM devices;

-- Alert counts in period
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE status != 'CLOSED') AS unresolved
FROM alerts
WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL;

-- MTTR (mean time to resolve, in minutes)
SELECT AVG(EXTRACT(EPOCH FROM (closed_at - created_at)) / 60.0)
FROM alerts
WHERE status = 'CLOSED'
  AND created_at >= NOW() - ($1 || ' days')::INTERVAL;

-- Top alerting devices
SELECT device_id, COUNT(*) AS cnt
FROM alerts
WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
GROUP BY device_id
ORDER BY cnt DESC
LIMIT 5;
```

## New endpoint: GET /customer/reports/sla-summary

Query params: `days: int = Query(30, ge=1, le=365)`

Logic:
1. Call `generate_sla_report(pool, tenant_id, days)`
2. Record in `report_runs` with `report_type = 'sla_summary'`
3. Return JSON

## New file: `services/ui_iot/workers/report_worker.py`

```python
async def run_report_tick(pool):
    """
    Called daily (86400s interval).
    For each distinct tenant_id that has at least one active device:
      - generate_sla_report(pool, tenant_id, days=30)
      - Insert result into report_runs.parameters (JSONB) with status='done'
    Log total tenants processed and any errors.
    """
```

Register in `services/ui_iot/main.py` alongside other worker loops:
```python
asyncio.create_task(worker_loop(run_report_tick, pool, interval=86400))
```

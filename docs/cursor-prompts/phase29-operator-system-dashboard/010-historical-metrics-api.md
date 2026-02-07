# Phase 29.10: Historical Metrics API

## Task

Add API endpoints that return time-series data for charting, querying the `system_metrics` InfluxDB database.

---

## Add History Endpoints

**File:** `services/ui_iot/routes/system.py`

Add new endpoints for historical data:

```python
from typing import Literal

@router.get("/metrics/history")
async def get_metrics_history(
    request: Request,
    metric: str = Query(..., description="Metric name: ingest_rate, queue_depth, connections, etc."),
    minutes: int = Query(15, ge=1, le=1440, description="Minutes of history to return"),
    resolution: int = Query(5, ge=5, le=300, description="Resolution in seconds"),
):
    """
    Get historical time-series data for a specific metric.
    Used for sparkline charts on the dashboard.
    """
    # Map metric names to InfluxDB queries
    metric_queries = {
        # Ingest metrics
        "messages_received": ("service_metrics", "messages_received", "service='ingest'"),
        "messages_written": ("service_metrics", "messages_written", "service='ingest'"),
        "messages_rejected": ("service_metrics", "messages_rejected", "service='ingest'"),
        "queue_depth": ("service_metrics", "queue_depth", "service='ingest'"),

        # Evaluator metrics
        "rules_evaluated": ("service_metrics", "rules_evaluated", "service='evaluator'"),
        "alerts_created": ("service_metrics", "alerts_created", "service='evaluator'"),

        # Dispatcher metrics
        "alerts_processed": ("service_metrics", "alerts_processed", "service='dispatcher'"),

        # Delivery metrics
        "jobs_succeeded": ("service_metrics", "jobs_succeeded", "service='delivery'"),
        "jobs_failed": ("service_metrics", "jobs_failed", "service='delivery'"),
        "jobs_pending": ("service_metrics", "jobs_pending", "service='delivery'"),

        # Postgres metrics
        "connections": ("postgres_metrics", "connections", None),
        "db_size_bytes": ("postgres_metrics", "db_size_bytes", None),

        # Platform metrics
        "devices_online": ("platform_metrics", "devices_online", None),
        "devices_stale": ("platform_metrics", "devices_stale", None),
        "alerts_open": ("platform_metrics", "alerts_open", None),
        "deliveries_pending": ("platform_metrics", "deliveries_pending", None),
    }

    if metric not in metric_queries:
        raise HTTPException(400, f"Unknown metric: {metric}. Available: {list(metric_queries.keys())}")

    measurement, field, where_clause = metric_queries[metric]

    # Build query with time bucketing for resolution
    where = f"WHERE time >= now() - INTERVAL '{minutes} minutes'"
    if where_clause:
        where += f" AND {where_clause}"

    # For rate metrics (counters), calculate difference between samples
    is_counter = metric in ["messages_received", "messages_written", "messages_rejected",
                            "rules_evaluated", "alerts_created", "alerts_processed",
                            "jobs_succeeded", "jobs_failed"]

    if is_counter:
        # For counters, we want the rate (difference between consecutive values)
        query = f"""
            SELECT
                time,
                {field} as value
            FROM {measurement}
            {where}
            ORDER BY time ASC
        """
    else:
        # For gauges, just get the value
        query = f"""
            SELECT
                time,
                {field} as value
            FROM {measurement}
            {where}
            ORDER BY time ASC
        """

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                json={"db": "system_metrics", "q": query, "format": "json"},
                headers={
                    "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                    "Content-Type": "application/json",
                },
            )

            if resp.status_code == 200:
                data = resp.json()

                # Convert to chart-friendly format
                points = []
                prev_value = None

                for row in data:
                    ts = row.get("time")
                    value = row.get("value", 0)

                    if is_counter and prev_value is not None:
                        # Calculate rate (difference / interval)
                        rate = max(0, value - prev_value) / resolution
                        points.append({"time": ts, "value": round(rate, 2)})
                    elif not is_counter:
                        points.append({"time": ts, "value": value})

                    prev_value = value

                return {
                    "metric": metric,
                    "points": points,
                    "minutes": minutes,
                    "resolution": resolution,
                    "is_rate": is_counter,
                }
            else:
                return {"metric": metric, "points": [], "error": resp.text}

    except Exception as e:
        logger.error("Failed to fetch metric history: %s", e)
        return {"metric": metric, "points": [], "error": str(e)}


@router.get("/metrics/history/batch")
async def get_metrics_history_batch(
    request: Request,
    metrics: str = Query(..., description="Comma-separated metric names"),
    minutes: int = Query(15, ge=1, le=1440),
):
    """
    Get historical data for multiple metrics in one request.
    More efficient for loading the dashboard.
    """
    import asyncio

    metric_list = [m.strip() for m in metrics.split(",")]

    # Fetch all metrics in parallel
    results = await asyncio.gather(
        *[
            get_metrics_history(request, metric=m, minutes=minutes, resolution=5)
            for m in metric_list
        ],
        return_exceptions=True,
    )

    response = {}
    for metric, result in zip(metric_list, results):
        if isinstance(result, Exception):
            response[metric] = {"points": [], "error": str(result)}
        else:
            response[metric] = result

    return response


@router.get("/metrics/latest")
async def get_latest_metrics(request: Request):
    """
    Get the most recent value for all tracked metrics.
    Single efficient query for dashboard initial load.
    """
    queries = {
        "ingest": """
            SELECT messages_received, messages_written, messages_rejected, queue_depth
            FROM service_metrics
            WHERE service = 'ingest'
            ORDER BY time DESC LIMIT 1
        """,
        "evaluator": """
            SELECT rules_evaluated, alerts_created
            FROM service_metrics
            WHERE service = 'evaluator'
            ORDER BY time DESC LIMIT 1
        """,
        "dispatcher": """
            SELECT alerts_processed, routes_matched
            FROM service_metrics
            WHERE service = 'dispatcher'
            ORDER BY time DESC LIMIT 1
        """,
        "delivery": """
            SELECT jobs_succeeded, jobs_failed, jobs_pending
            FROM service_metrics
            WHERE service = 'delivery'
            ORDER BY time DESC LIMIT 1
        """,
        "postgres": """
            SELECT connections, db_size_bytes
            FROM postgres_metrics
            ORDER BY time DESC LIMIT 1
        """,
        "platform": """
            SELECT devices_online, devices_stale, alerts_open, deliveries_pending
            FROM platform_metrics
            ORDER BY time DESC LIMIT 1
        """,
    }

    results = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, query in queries.items():
            try:
                resp = await client.post(
                    f"{INFLUXDB_URL}/api/v3/query_sql",
                    json={"db": "system_metrics", "q": query, "format": "json"},
                    headers={
                        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results[name] = data[0] if data else {}
                else:
                    results[name] = {"error": resp.text}
            except Exception as e:
                results[name] = {"error": str(e)}

    return results
```

---

## Update API Types

**File:** `frontend/src/services/api/system.ts`

Add new types and functions:

```typescript
export interface MetricPoint {
  time: string;
  value: number;
}

export interface MetricHistory {
  metric: string;
  points: MetricPoint[];
  minutes: number;
  resolution: number;
  is_rate: boolean;
  error?: string;
}

export interface MetricHistoryBatch {
  [metric: string]: MetricHistory;
}

export async function fetchMetricHistory(
  metric: string,
  minutes = 15
): Promise<MetricHistory> {
  const response = await apiClient.get(
    `/operator/system/metrics/history?metric=${metric}&minutes=${minutes}`
  );
  return response.data;
}

export async function fetchMetricHistoryBatch(
  metrics: string[],
  minutes = 15
): Promise<MetricHistoryBatch> {
  const response = await apiClient.get(
    `/operator/system/metrics/history/batch?metrics=${metrics.join(",")}&minutes=${minutes}`
  );
  return response.data;
}

export async function fetchLatestMetrics(): Promise<Record<string, Record<string, number>>> {
  const response = await apiClient.get("/operator/system/metrics/latest");
  return response.data;
}
```

---

## Verification

```bash
# Restart UI (after implementing collector)
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Wait 30 seconds for metrics to accumulate, then test
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/operator/system/metrics/history?metric=queue_depth&minutes=5"

curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/operator/system/metrics/history/batch?metrics=queue_depth,connections,alerts_open&minutes=15"
```

Expected response:
```json
{
  "metric": "queue_depth",
  "points": [
    {"time": "2024-01-15T10:00:00Z", "value": 0},
    {"time": "2024-01-15T10:00:05Z", "value": 2},
    {"time": "2024-01-15T10:00:10Z", "value": 0}
  ],
  "minutes": 5,
  "resolution": 5,
  "is_rate": false
}
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/system.py` |
| MODIFY | `frontend/src/services/api/system.ts` |

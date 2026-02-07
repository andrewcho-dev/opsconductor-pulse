# Phase 29.3: System Throughput Metrics API

## Task

Create `/operator/system/metrics` endpoint that returns real-time throughput and latency metrics.

---

## Add Metrics Endpoint

**File:** `services/ui_iot/routes/system.py`

Add to the existing system router:

```python
@router.get("/metrics")
async def get_system_metrics(request: Request):
    """
    Get system throughput and latency metrics.
    Aggregates data from service health endpoints and InfluxDB.
    """
    import asyncio

    # Fetch counters from services
    service_metrics = await asyncio.gather(
        fetch_service_counters(INGEST_URL),
        fetch_service_counters(EVALUATOR_URL),
        fetch_service_counters(DISPATCHER_URL),
        fetch_service_counters(DELIVERY_URL),
        return_exceptions=True,
    )

    ingest_counters = service_metrics[0] if not isinstance(service_metrics[0], Exception) else {}
    evaluator_counters = service_metrics[1] if not isinstance(service_metrics[1], Exception) else {}
    dispatcher_counters = service_metrics[2] if not isinstance(service_metrics[2], Exception) else {}
    delivery_counters = service_metrics[3] if not isinstance(service_metrics[3], Exception) else {}

    # Calculate rates from InfluxDB (messages in last minute)
    ingest_rate = await calculate_ingest_rate()

    return {
        "throughput": {
            "ingest_rate_per_sec": ingest_rate,
            "messages_received_total": ingest_counters.get("messages_received", 0),
            "messages_written_total": ingest_counters.get("messages_written", 0),
            "messages_rejected_total": ingest_counters.get("messages_rejected", 0),
            "alerts_created_total": evaluator_counters.get("alerts_created", 0),
            "alerts_dispatched_total": dispatcher_counters.get("alerts_processed", 0),
            "deliveries_succeeded_total": delivery_counters.get("jobs_succeeded", 0),
            "deliveries_failed_total": delivery_counters.get("jobs_failed", 0),
        },
        "queues": {
            "ingest_queue_depth": ingest_counters.get("queue_depth", 0),
            "delivery_pending": delivery_counters.get("jobs_pending", 0),
        },
        "last_activity": {
            "last_ingest": ingest_counters.get("last_write_at"),
            "last_evaluation": evaluator_counters.get("last_evaluation_at"),
            "last_dispatch": dispatcher_counters.get("last_dispatch_at"),
            "last_delivery": delivery_counters.get("last_delivery_at"),
        },
        "period": "since_service_start",
    }


async def fetch_service_counters(url: str) -> dict:
    """Fetch counters from a service health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            if resp.status_code == 200:
                data = resp.json()
                counters = data.get("counters", {})
                # Also include last_* timestamps
                for key in ["last_write_at", "last_evaluation_at", "last_dispatch_at", "last_delivery_at"]:
                    if key in data:
                        counters[key] = data[key]
                return counters
    except Exception as e:
        logger.warning("Failed to fetch counters from %s: %s", url, e)
    return {}


async def calculate_ingest_rate() -> float:
    """Calculate messages per second from InfluxDB (last 60 seconds)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Query telemetry count in last 60 seconds across all tenant databases
            # This is approximate - we query one database as a sample
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                json={
                    "db": "telemetry_enabled",  # Sample database
                    "q": "SELECT COUNT(*) as count FROM telemetry WHERE time >= now() - INTERVAL '60 seconds'",
                    "format": "json",
                },
                headers={
                    "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                    "Content-Type": "application/json",
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    count = data[0].get("count", 0)
                    return round(count / 60.0, 2)
    except Exception as e:
        logger.warning("Failed to calculate ingest rate: %s", e)

    return 0.0
```

---

## Historical Metrics (Optional Enhancement)

For more accurate rate calculations, store periodic snapshots:

```python
# In-memory rate tracker (simple approach)
import threading
from collections import deque
from datetime import datetime

class RateTracker:
    """Track message rates over time."""

    def __init__(self, window_seconds: int = 300):
        self.window = window_seconds
        self.samples: deque = deque(maxlen=window_seconds)
        self._lock = threading.Lock()

    def record(self, count: int):
        """Record a sample."""
        with self._lock:
            self.samples.append((datetime.utcnow(), count))

    def get_rate(self) -> float:
        """Calculate rate from samples."""
        with self._lock:
            if len(self.samples) < 2:
                return 0.0
            oldest = self.samples[0]
            newest = self.samples[-1]
            time_diff = (newest[0] - oldest[0]).total_seconds()
            if time_diff <= 0:
                return 0.0
            count_diff = newest[1] - oldest[1]
            return round(count_diff / time_diff, 2)

# Global tracker (would need periodic polling to populate)
ingest_rate_tracker = RateTracker()
```

---

## Verification

```bash
# Restart UI
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Test metrics endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8080/operator/system/metrics
```

Expected response:
```json
{
  "throughput": {
    "ingest_rate_per_sec": 125.5,
    "messages_received_total": 450000,
    "messages_written_total": 449500,
    "messages_rejected_total": 500,
    "alerts_created_total": 1250,
    "alerts_dispatched_total": 1250,
    "deliveries_succeeded_total": 1180,
    "deliveries_failed_total": 70
  },
  "queues": {
    "ingest_queue_depth": 0,
    "delivery_pending": 3
  },
  "last_activity": {
    "last_ingest": "2024-01-15T10:00:00Z",
    "last_evaluation": "2024-01-15T10:00:00Z",
    "last_dispatch": "2024-01-15T10:00:00Z",
    "last_delivery": "2024-01-15T09:59:58Z"
  },
  "period": "since_service_start"
}
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/system.py` |

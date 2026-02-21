# Prompt 001 — Shared Metrics Module + Requirements

## Add prometheus_client to requirements

Add `prometheus_client>=0.20.0` to:
- `services/ui_iot/requirements.txt`
- `services/ingest_iot/requirements.txt`
- `services/evaluator_iot/requirements.txt`

## Create `services/shared/metrics.py`

```python
"""
Shared Prometheus metrics registry.

Each service imports and increments these counters/gauges.
Use the REGISTRY directly with prometheus_client.generate_latest().
"""

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, REGISTRY

# ── Ingest ───────────────────────────────────────────────────────────────────
ingest_messages_total = Counter(
    "pulse_ingest_messages_total",
    "Total MQTT messages processed",
    ["tenant_id", "result"],  # result: accepted | rejected | rate_limited
)

ingest_queue_depth = Gauge(
    "pulse_ingest_queue_depth",
    "Current ingest processing queue depth",
)

# ── Evaluator ─────────────────────────────────────────────────────────────────
evaluator_rules_evaluated_total = Counter(
    "pulse_evaluator_rules_evaluated_total",
    "Total alert rule evaluations",
    ["tenant_id"],
)

evaluator_alerts_created_total = Counter(
    "pulse_evaluator_alerts_created_total",
    "Total alerts created or updated",
    ["tenant_id"],
)

evaluator_evaluation_errors_total = Counter(
    "pulse_evaluator_evaluation_errors_total",
    "Total evaluation errors",
)

# ── UI / Fleet ────────────────────────────────────────────────────────────────
fleet_active_alerts = Gauge(
    "pulse_fleet_active_alerts",
    "Current count of OPEN+ACKNOWLEDGED alerts",
    ["tenant_id"],
)

fleet_devices_by_status = Gauge(
    "pulse_fleet_devices_by_status",
    "Current device count by status",
    ["tenant_id", "status"],  # status: ONLINE | STALE | OFFLINE
)

delivery_jobs_failed_total = Counter(
    "pulse_delivery_jobs_failed_total",
    "Total delivery jobs that reached FAILED status",
    ["tenant_id"],
)
```

## Acceptance Criteria

- [ ] `prometheus_client` added to all three requirements.txt files
- [ ] `services/shared/metrics.py` created with all metric objects above
- [ ] Module importable without error: `python -c "from shared.metrics import ingest_messages_total"`

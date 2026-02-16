"""
Shared Prometheus metrics registry.

Each service imports and increments these counters/gauges.
Use prometheus_client.generate_latest() in service /metrics handlers.
"""

from prometheus_client import Counter, Gauge, Histogram

# Ingest
ingest_messages_total = Counter(
    "pulse_ingest_messages_total",
    "Total MQTT messages processed",
    ["tenant_id", "result"],  # accepted | rejected | rate_limited
)

ingest_queue_depth = Gauge(
    "pulse_ingest_queue_depth",
    "Current ingest processing queue depth",
)

# Evaluator
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

# UI/Fleet
fleet_active_alerts = Gauge(
    "pulse_fleet_active_alerts",
    "Current count of OPEN+ACKNOWLEDGED alerts",
    ["tenant_id"],
)

fleet_devices_by_status = Gauge(
    "pulse_fleet_devices_by_status",
    "Current device count by status",
    ["tenant_id", "status"],
)

delivery_jobs_failed_total = Counter(
    "pulse_delivery_jobs_failed_total",
    "Total delivery jobs that reached FAILED status",
    ["tenant_id"],
)

# HTTP request metrics
http_request_duration_seconds = Histogram(
    "pulse_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path_template", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_total = Counter(
    "pulse_http_requests_total",
    "Total HTTP requests",
    ["method", "path_template", "status_code"],
)

# Auth failure metrics
pulse_auth_failures_total = Counter(
    "pulse_auth_failures_total",
    "Total authentication failures by reason",
    ["reason"],
)

# Per-service operational metrics
pulse_queue_depth = Gauge(
    "pulse_queue_depth",
    "Current queue depth for a service processing queue",
    ["service", "queue_name"],
)

pulse_processing_duration_seconds = Histogram(
    "pulse_processing_duration_seconds",
    "Duration of a processing cycle in seconds",
    ["service", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

pulse_db_pool_size = Gauge(
    "pulse_db_pool_size",
    "Current total size of the database connection pool",
    ["service"],
)

pulse_db_pool_free = Gauge(
    "pulse_db_pool_free",
    "Current number of free (idle) connections in the pool",
    ["service"],
)

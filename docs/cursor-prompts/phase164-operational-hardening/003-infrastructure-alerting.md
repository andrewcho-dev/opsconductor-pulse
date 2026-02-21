# Task 3: Infrastructure Alert Rules

## File to Modify

- `compose/prometheus/alert_rules.yml`

## What to Do

Add Prometheus alert rules for the key scaling and reliability indicators.

```yaml
groups:
  - name: pulse_infrastructure
    interval: 30s
    rules:

      # ─── NATS Consumer Lag ───────────────────────────────
      - alert: NATSConsumerLagHigh
        expr: nats_consumer_num_pending{consumer="ingest-workers"} > 10000
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "NATS ingest consumer lag is {{ $value }} messages"
          description: "Ingest workers are falling behind. Consider scaling up ingest pods."

      - alert: NATSConsumerLagCritical
        expr: nats_consumer_num_pending{consumer="ingest-workers"} > 50000
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "NATS ingest consumer lag critical: {{ $value }} messages"

      # ─── Batch Write Latency ─────────────────────────────
      - alert: BatchWriteLatencyHigh
        expr: histogram_quantile(0.95, rate(pulse_ingest_batch_write_seconds_bucket[5m])) > 2
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "P95 batch write latency is {{ $value }}s"
          description: "Database writes are slow. Check PG performance and pool utilization."

      # ─── EMQX Connections ────────────────────────────────
      - alert: EMQXConnectionsHigh
        expr: emqx_connections_count > 50000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "EMQX has {{ $value }} active connections"
          description: "Approaching connection limits. Consider adding EMQX cluster nodes."

      # ─── Route Delivery DLQ ──────────────────────────────
      - alert: DLQDepthGrowing
        expr: increase(pulse_delivery_dlq_total[1h]) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "{{ $value }} messages sent to DLQ in the last hour"
          description: "Check webhook destinations for failures."

      # ─── Route Delivery Lag ──────────────────────────────
      - alert: RouteDeliveryLagHigh
        expr: nats_consumer_num_pending{consumer="route-delivery"} > 1000
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Route delivery consumer lag: {{ $value }}"

      # ─── DB Pool Saturation ──────────────────────────────
      - alert: DBPoolSaturated
        expr: pulse_db_pool_active / pulse_db_pool_max > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DB pool {{ $value }}% utilized"
          description: "Consider increasing PG_POOL_MAX or scaling DB instance."

      # ─── Service Down ────────────────────────────────────
      - alert: IngestServiceDown
        expr: up{job="ingest"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Ingest service is down"

      - alert: RouteDeliveryDown
        expr: up{job="route-delivery"} == 0
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Route delivery service is down"

      - alert: EMQXDown
        expr: up{job="emqx"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "EMQX broker is down"

      - alert: NATSDown
        expr: up{job="nats"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "NATS is down"
```

## Important Notes

- **Metric names are approximate** — verify against actual Prometheus metric names exposed by NATS and EMQX. The exact names depend on the exporter version.
- **For NATS metrics:** Use the built-in `/metrics` endpoint or the `nats-server-exporter`.
- **For EMQX metrics:** EMQX 5.x exposes Prometheus-format metrics at `/api/v5/prometheus/stats`.
- **DB pool metrics:** The services need to expose pool utilization as a Prometheus gauge. Add this to the health/metrics endpoints in each service.
- **Alert routing:** Configure Alertmanager to send critical alerts to PagerDuty/Slack and warnings to a monitoring channel.

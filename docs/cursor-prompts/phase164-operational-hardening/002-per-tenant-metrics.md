# Task 2: Per-Tenant Metrics and Grafana Dashboards

## Files to Modify

- `services/ingest_iot/ingest.py` — ensure `tenant_id` label on all metrics
- `services/route_delivery/delivery.py` — add Prometheus metrics
- `compose/prometheus/alert_rules.yml` — add scaling-relevant alerts
- `compose/grafana/provisioning/dashboards/` — add tenant and infrastructure dashboards

## What to Do

### Step 1: Verify ingest metrics have tenant_id label

The ingest service already has `pulse_ingest_messages_total` with `tenant_id` and `result` labels. Verify these additional metrics exist or add them:

```python
# Per-tenant metrics
ingest_messages_total = Counter("pulse_ingest_messages_total", "Total ingested messages", ["tenant_id", "result"])
ingest_batch_write_seconds = Histogram("pulse_ingest_batch_write_seconds", "Batch write latency", ["tenant_id"])
ingest_queue_depth = Gauge("pulse_ingest_nats_pending", "NATS consumer pending messages")
```

### Step 2: Add metrics to route delivery service

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

delivery_total = Counter("pulse_delivery_total", "Route deliveries", ["tenant_id", "destination_type", "result"])
delivery_latency = Histogram("pulse_delivery_seconds", "Delivery latency", ["destination_type"])
delivery_dlq_total = Counter("pulse_delivery_dlq_total", "DLQ writes", ["tenant_id"])

# Start metrics server on port 8080
start_http_server(8080)
```

### Step 3: Add EMQX and NATS scrape targets to Prometheus

Update `compose/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  # ... existing targets ...

  - job_name: emqx
    metrics_path: /api/v5/prometheus/stats
    static_targets:
      - targets: ["iot-mqtt:18083"]
    # EMQX 5.x exposes Prometheus metrics natively

  - job_name: nats
    metrics_path: /metrics
    static_targets:
      - targets: ["iot-nats:8222"]
    # NATS exposes Prometheus metrics on the monitoring port

  - job_name: route-delivery
    static_targets:
      - targets: ["iot-route-delivery:8080"]
```

### Step 4: Create Grafana dashboards

Create two new dashboard JSON files in `compose/grafana/provisioning/dashboards/`:

**tenant-overview.json:**
- Per-tenant message throughput (rate of `pulse_ingest_messages_total` by tenant_id)
- Per-tenant rejection rate (result=rejected by tenant_id)
- Top 10 tenants by message volume
- Per-tenant webhook delivery success rate

**infrastructure.json:**
- NATS consumer lag (pending messages per consumer)
- EMQX connection count (total + per listener)
- EMQX message throughput (publish rate)
- Ingest batch write latency histogram
- DB connection pool utilization (active vs max)
- Route delivery latency histogram
- DLQ depth (total pending dead letter messages)

### Step 5: EMQX dashboard metrics to expose

EMQX 5.x provides these Prometheus metrics natively:
- `emqx_connections_count` — total MQTT connections
- `emqx_messages_received` — messages received from clients
- `emqx_messages_sent` — messages sent to clients
- `emqx_messages_publish` — messages published
- `emqx_client_connect` — connection events
- `emqx_client_auth_anonymous` — anonymous auth attempts (should be 0)

## Important Notes

- **Cardinality warning:** The `tenant_id` label creates a time series per tenant. At 500 tenants, this is manageable. At 10K+ tenants, consider using recording rules to pre-aggregate.
- **EMQX Prometheus:** Must be enabled in emqx.conf: `prometheus { push_gateway_server = "" }` (or just scrape the HTTP endpoint).
- **NATS monitoring:** Available at `http://iot-nats:8222/` with endpoints `/varz`, `/connz`, `/jsz`, `/routez`.

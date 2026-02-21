# 139-003: Pre-Built Grafana Dashboards

## Task
Create 6 provisioned Grafana dashboards as JSON files.

## Location
`compose/grafana/dashboards/`

## Metrics Available (from services/shared/metrics.py)
These are the Prometheus metrics already exposed by OpsConductor services:

| Metric Name | Type | Labels | Source |
|---|---|---|---|
| `pulse_http_requests_total` | Counter | service, method, path, status | ui_iot |
| `pulse_http_request_duration_seconds` | Histogram | service, method, path | ui_iot |
| `pulse_auth_failures_total` | Counter | service, reason | ui_iot |
| `pulse_ingest_messages_total` | Counter | tenant_id, msg_type | ingest |
| `pulse_ingest_queue_depth` | Gauge | — | ingest |
| `pulse_evaluator_rules_evaluated_total` | Counter | — | evaluator |
| `pulse_evaluator_alerts_created_total` | Counter | severity | evaluator |
| `pulse_evaluator_evaluation_errors_total` | Counter | — | evaluator |
| `pulse_fleet_active_alerts` | Gauge | tenant_id, severity | evaluator |
| `pulse_fleet_devices_by_status` | Gauge | tenant_id, status | evaluator |
| `pulse_delivery_jobs_failed_total` | Counter | channel_type | ops_worker |
| `pulse_queue_depth` | Gauge | service | ops_worker |
| `pulse_processing_duration_seconds` | Histogram | service, operation | ops_worker |
| `pulse_db_pool_size` | Gauge | service | all services |
| `pulse_db_pool_free` | Gauge | service | all services |

Plus standard `process_*`, `python_*` metrics from prometheus_client.

## Dashboard 1: API Overview
**File**: `compose/grafana/dashboards/api-overview.json`

Create a Grafana dashboard JSON with panels:

1. **HTTP Request Rate** (graph): `rate(pulse_http_requests_total[5m])` grouped by status code
2. **Latency p50/p95/p99** (graph): `histogram_quantile(0.5, rate(pulse_http_request_duration_seconds_bucket[5m]))` etc.
3. **Error Rate %** (stat): `sum(rate(pulse_http_requests_total{status=~"5.."}[5m])) / sum(rate(pulse_http_requests_total[5m])) * 100`
4. **Status Code Distribution** (pie chart): `sum by (status) (increase(pulse_http_requests_total[1h]))`
5. **Top Endpoints by Request Volume** (table): `topk(10, sum by (path) (rate(pulse_http_requests_total[5m])))`
6. **Request Volume** (stat): `sum(rate(pulse_http_requests_total[5m]))`

**Grafana JSON structure**: Use the standard Grafana dashboard JSON format. The simplest approach is to create the dashboard in Grafana UI first, then export as JSON. But for provisioning, create the JSON directly:

```json
{
  "dashboard": {
    "id": null,
    "uid": "api-overview",
    "title": "API Overview",
    "tags": ["opsconductor", "api"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "HTTP Request Rate",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
          {
            "expr": "sum by (status) (rate(pulse_http_requests_total[5m]))",
            "legendFormat": "{{status}}"
          }
        ]
      }
      // ... more panels
    ],
    "time": {"from": "now-1h", "to": "now"},
    "refresh": "30s"
  }
}
```

**Important**: For provisioned dashboards, the JSON file should contain JUST the dashboard object (no wrapper `{"dashboard": ...}`). Check Grafana provisioning docs for the correct format.

## Dashboard 2: Auth & Security
**File**: `compose/grafana/dashboards/auth-security.json`

Panels:
1. **Auth Failure Rate** (graph): `rate(pulse_auth_failures_total[5m])` by reason
2. **Auth Failures Total** (stat): `sum(increase(pulse_auth_failures_total[1h]))`
3. **Successful Logins Rate** (graph): `rate(pulse_http_requests_total{path="/auth/login",status="200"}[5m])` (adjust path as needed)

## Dashboard 3: Alert Pipeline
**File**: `compose/grafana/dashboards/alert-pipeline.json`

Panels:
1. **Rules Evaluated/s** (stat): `rate(pulse_evaluator_rules_evaluated_total[5m])`
2. **Alerts Created/s** (graph): `rate(pulse_evaluator_alerts_created_total[5m])` by severity
3. **Evaluation Errors** (graph): `rate(pulse_evaluator_evaluation_errors_total[5m])`
4. **Active Alerts by Severity** (bar gauge): `pulse_fleet_active_alerts` by severity
5. **Delivery Failures** (graph): `rate(pulse_delivery_jobs_failed_total[5m])` by channel_type

## Dashboard 4: Device Fleet
**File**: `compose/grafana/dashboards/device-fleet.json`

Panels:
1. **Devices by Status** (pie chart): `pulse_fleet_devices_by_status` by status
2. **Total Connected Devices** (stat): `sum(pulse_fleet_devices_by_status{status="ONLINE"})`
3. **Telemetry Ingestion Rate** (graph): `rate(pulse_ingest_messages_total[5m])` by msg_type
4. **Ingest Queue Depth** (graph): `pulse_ingest_queue_depth`
5. **Devices by Tenant** (bar chart): `sum by (tenant_id) (pulse_fleet_devices_by_status)`

## Dashboard 5: Database
**File**: `compose/grafana/dashboards/database.json`

Panels:
1. **DB Pool Size** (graph): `pulse_db_pool_size` by service
2. **DB Pool Free Connections** (graph): `pulse_db_pool_free` by service
3. **Pool Utilization %** (gauge): `(1 - pulse_db_pool_free / pulse_db_pool_size) * 100` by service
4. **Worker Processing Duration** (graph): `histogram_quantile(0.95, rate(pulse_processing_duration_seconds_bucket[5m]))` by operation

## Dashboard 6: Service Health
**File**: `compose/grafana/dashboards/service-health.json`

Panels:
1. **Service Up/Down** (stat with thresholds): `up` metric by job, green=1, red=0
2. **Process Memory** (graph): `process_resident_memory_bytes` by job
3. **Process CPU** (graph): `rate(process_cpu_seconds_total[5m])` by job
4. **Open File Descriptors** (graph): `process_open_fds` by job
5. **Worker Queue Depth** (graph): `pulse_queue_depth` by service

## Tips for Dashboard JSON
- Use `"uid"` to create stable references (e.g., `"api-overview"`, `"auth-security"`)
- Set `"editable": true` so users can customize
- Use variables for time range: `$__interval`, `$__range`
- Set reasonable defaults: 1h time range, 30s refresh
- Each panel needs: `id`, `title`, `type`, `gridPos`, `datasource`, `targets`
- Panel types: `timeseries` (graphs), `stat` (single value), `gauge`, `piechart`, `table`, `bargauge`

## Verification
```bash
docker compose up -d prometheus grafana
# Wait for Grafana startup
```

Open http://localhost:3001:
- Navigate to Dashboards → OpsConductor Pulse folder
- Should see 6 dashboards
- Open "API Overview" → panels should show live data (if services are running and generating traffic)
- Open "Device Fleet" → should show device counts and ingestion rates
- Open "Service Health" → should show all services as "UP"

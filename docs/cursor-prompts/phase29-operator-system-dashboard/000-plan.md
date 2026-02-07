# Phase 29: Operator System Dashboard

## Summary

Build a "galactic control view" dashboard for operators showing real-time infrastructure health, system throughput, capacity utilization, and aggregate metrics across the entire platform.

**Why**: Operators need visibility into the overall system state, not just individual tenants. When something goes wrong, they need to see it immediately. When capacity is running low, they need to know before it becomes critical.

---

## Dashboard Sections

### 1. Service Health Grid
Visual status indicators for each core component:

| Service | Health Check | Key Metrics |
|---------|--------------|-------------|
| PostgreSQL | `pg_isready` + connection test | connections, db size |
| InfluxDB | `/health` endpoint | file count, write latency |
| MQTT Broker | Connection test | connected clients |
| Keycloak | `/health` endpoint | active sessions |
| Ingest Service | Custom health + metrics | messages/sec, queue depth |
| Evaluator | Custom health | rules evaluated/sec |
| Dispatcher | Custom health | alerts dispatched/sec |
| Delivery Worker | Custom health | pending deliveries |

Status: 🟢 Healthy | 🟡 Degraded | 🔴 Down | ⚪ Unknown

### 2. System Throughput (Real-time)
- **Ingestion rate**: messages/sec (line chart, last 15 min)
- **Write latency**: p50/p95/p99 to InfluxDB
- **Alert rate**: alerts created/sec
- **Delivery rate**: webhooks sent/sec

### 3. Capacity Gauges
- **Disk Usage**: Postgres data, InfluxDB data, total volume
- **Database Size**: Postgres DB size, InfluxDB file count
- **Connections**: Postgres connections used/max
- **Memory**: Container memory usage per service

### 4. Aggregate Platform Metrics
- Total tenants (active / suspended / deleted)
- Total devices (registered / online / stale)
- Total alerts (open / closed today / triggered today)
- Total integrations (active webhooks / email / SMS)

### 5. Recent Events / Errors
- Last 10 system errors (ingest failures, delivery failures, etc.)
- Rate limit events
- Authentication failures
- Quarantined messages count

---

## Data Sources

### PostgreSQL Metrics
```sql
-- Database size
SELECT pg_database_size('iotcloud') as db_size;

-- Connection count
SELECT count(*) FROM pg_stat_activity WHERE datname = 'iotcloud';

-- Table sizes
SELECT relname, pg_total_relation_size(relid) as size
FROM pg_catalog.pg_statio_user_tables ORDER BY size DESC LIMIT 10;
```

### InfluxDB Metrics
- `GET /health` - basic health
- `GET /api/v3/query_sql?q=SELECT COUNT(*) FROM telemetry WHERE time > now() - INTERVAL '1 minute'` - recent writes
- File system check for data directory size and file count

### MQTT Broker (Mosquitto)
- Connect test with admin client
- Parse `$SYS/#` topics if enabled (connected clients, messages/sec)

### Container Metrics (via Docker Socket)
- CPU usage per container
- Memory usage per container
- Requires mounting `/var/run/docker.sock` into the UI container

### Application Metrics
Services expose internal counters:
- Ingest: messages_received, messages_written, queue_depth
- Evaluator: rules_evaluated, alerts_created
- Dispatcher: alerts_routed
- Delivery: webhooks_sent, webhooks_failed

---

## Architecture

### Option A: Poll from UI Service
UI service polls each component's health/metrics endpoint and aggregates.
- Pros: Simple, no new services
- Cons: UI service becomes a metrics aggregator

### Option B: Dedicated Metrics Service
New `metrics_collector` service that polls all components, stores in time-series.
- Pros: Cleaner separation, historical data
- Cons: Another service to maintain

### Option C: Prometheus + Grafana
Standard observability stack, services expose `/metrics` in Prometheus format.
- Pros: Industry standard, powerful
- Cons: Two more containers, separate UI from main app

**Recommendation**: Start with **Option A** (poll from UI service) for MVP. Migrate to Prometheus later if needed.

---

## API Endpoints

### GET /operator/system/health
Component health status with response times.

```json
{
  "status": "healthy",
  "components": {
    "postgres": {"status": "healthy", "latency_ms": 2, "connections": 15, "max_connections": 100},
    "influxdb": {"status": "healthy", "latency_ms": 5, "file_count": 432},
    "mqtt": {"status": "healthy", "connected_clients": 25},
    "keycloak": {"status": "healthy", "latency_ms": 12},
    "ingest": {"status": "healthy", "queue_depth": 0},
    "evaluator": {"status": "healthy"},
    "dispatcher": {"status": "healthy"},
    "delivery": {"status": "healthy", "pending_jobs": 3}
  },
  "checked_at": "2024-01-15T10:00:00Z"
}
```

### GET /operator/system/metrics
Real-time throughput metrics.

```json
{
  "throughput": {
    "ingest_rate_per_sec": 125.5,
    "alert_rate_per_sec": 2.3,
    "delivery_rate_per_sec": 1.8
  },
  "latency": {
    "influx_write_p50_ms": 3,
    "influx_write_p95_ms": 12,
    "influx_write_p99_ms": 45
  },
  "period": "last_60_seconds"
}
```

### GET /operator/system/capacity
Disk, memory, connection utilization.

```json
{
  "disk": {
    "postgres_data_gb": 12.5,
    "influxdb_data_gb": 45.2,
    "total_volume_gb": 100,
    "used_pct": 57.7
  },
  "postgres": {
    "db_size_mb": 1250,
    "connections_used": 15,
    "connections_max": 100
  },
  "influxdb": {
    "file_count": 432,
    "file_limit": 1000
  }
}
```

### GET /operator/system/aggregates
Platform-wide counts.

```json
{
  "tenants": {"active": 12, "suspended": 2, "total": 14},
  "devices": {"registered": 450, "online": 380, "stale": 70},
  "alerts": {"open": 23, "closed_today": 156, "triggered_today": 179},
  "integrations": {"total": 35, "active": 28}
}
```

### GET /operator/system/errors
Recent errors and failures.

```json
{
  "errors": [
    {"timestamp": "...", "service": "delivery", "type": "webhook_timeout", "message": "..."},
    ...
  ],
  "counts": {
    "ingest_failures_1h": 3,
    "delivery_failures_1h": 12,
    "auth_failures_1h": 45,
    "quarantined_1h": 7
  }
}
```

---

## Task Breakdown

| Phase | Prompt | Description |
|-------|--------|-------------|
| 1 | `001-health-endpoints.md` | Add health check endpoints for each service |
| 2 | `002-system-health-api.md` | Aggregate health API in UI service |
| 3 | `003-system-metrics-api.md` | Throughput and latency metrics API |
| 4 | `004-system-capacity-api.md` | Disk/connection capacity API |
| 5 | `005-system-aggregates-api.md` | Platform-wide aggregate counts |
| 6 | `006-system-errors-api.md` | Recent errors/failures API |
| 7 | `007-dashboard-ui.md` | Operator System Dashboard page |
| 8 | `008-auto-refresh.md` | Real-time updates via polling or WebSocket |

---

## UI Design

```
┌─────────────────────────────────────────────────────────────────────┐
│  SYSTEM STATUS                                          Last: 10s ago│
├─────────────────────────────────────────────────────────────────────┤
│  🟢 Postgres   🟢 InfluxDB   🟢 MQTT   🟢 Keycloak                  │
│  🟢 Ingest     🟢 Evaluator  🟢 Dispatcher  🟡 Delivery (3 pending) │
├─────────────────────────────────────────────────────────────────────┤
│  THROUGHPUT (last 15 min)                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  📈 Ingestion Rate: 125 msg/sec                              │   │
│  │  [=======================================================]   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  Write Latency: p50=3ms  p95=12ms  p99=45ms                         │
├──────────────────────────────────┬──────────────────────────────────┤
│  CAPACITY                        │  PLATFORM TOTALS                 │
│  ┌────────────────────────────┐  │  Tenants:     14 (12 active)     │
│  │  Disk: 58% [████████░░░░]  │  │  Devices:    450 (380 online)    │
│  │  PG Conn: 15/100           │  │  Alerts:      23 open            │
│  │  Influx Files: 432/1000    │  │  Integrations: 28 active         │
│  └────────────────────────────┘  │                                  │
├──────────────────────────────────┴──────────────────────────────────┤
│  RECENT ERRORS                                                      │
│  ⚠️ 10:02:15  delivery  webhook_timeout  https://example.com/hook   │
│  ⚠️ 10:01:45  ingest    parse_error      Invalid JSON from dev-042  │
│  ⚠️ 09:58:22  auth      token_expired    Device tok-abc123          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Files Overview

| File | Purpose |
|------|---------|
| `services/ui_iot/routes/system.py` | System metrics API endpoints |
| `frontend/src/features/operator/SystemDashboard.tsx` | Main dashboard page |
| `frontend/src/features/operator/components/ServiceHealthGrid.tsx` | Health status grid |
| `frontend/src/features/operator/components/ThroughputChart.tsx` | Real-time throughput |
| `frontend/src/features/operator/components/CapacityGauges.tsx` | Disk/connection gauges |
| `frontend/src/features/operator/components/ErrorFeed.tsx` | Recent errors list |
| `frontend/src/services/api/system.ts` | API client for system endpoints |

---

## Dependencies

- Services need to expose health endpoints (some already do)
- May need Docker socket access for container metrics (optional for MVP)
- Consider adding Postgres `pg_stat_statements` extension for query metrics

---

## Future Enhancements

- Historical metrics storage (keep 7 days of system metrics)
- Alerting on system thresholds (disk > 80%, error rate spike)
- Service dependency graph visualization
- Log aggregation view
- Prometheus/Grafana migration path

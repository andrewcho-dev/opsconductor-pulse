# Phase 30.14: Update All Documentation

## Task

Update all documentation to reflect the migration from InfluxDB to TimescaleDB.

---

## README.md Updates

### Line 8 - Multi-tenant isolation
**Change from:**
```markdown
- **Multi-tenant isolation** — JWT claims + database RLS + per-tenant InfluxDB databases
```
**To:**
```markdown
- **Multi-tenant isolation** — JWT claims + database RLS + tenant_id column filtering
```

### Line 11 - Time-series storage
**Change from:**
```markdown
- **InfluxDB time-series** — InfluxDB 3 Core with per-tenant databases, batched writes
```
**To:**
```markdown
- **TimescaleDB time-series** — PostgreSQL with TimescaleDB extension, hypertables, compression, batched writes
```

### Lines 40-41 - Quick Start services
**Remove:**
```markdown
# InfluxDB:           localhost:8181
```

### Line 96 - Services table
**Change from:**
```markdown
  ingest_iot/           # MQTT device ingestion, auth cache, batched InfluxDB writes
```
**To:**
```markdown
  ingest_iot/           # MQTT device ingestion, auth cache, batched TimescaleDB writes
```

### Lines 114-115 - Services Overview table
**Change from:**
```markdown
| **ingest_iot** | MQTT device ingress with auth caching, multi-worker pipeline, batched InfluxDB writes |
| **evaluator_iot** | Device state tracking, NO_HEARTBEAT alerts, threshold rule evaluation from InfluxDB |
```
**To:**
```markdown
| **ingest_iot** | MQTT device ingress with auth caching, multi-worker pipeline, batched TimescaleDB writes |
| **evaluator_iot** | Device state tracking, NO_HEARTBEAT alerts, threshold rule evaluation from TimescaleDB |
```

### Lines 260-261 - Security section
**Change from:**
```markdown
- **InfluxDB isolation** — Per-tenant databases for telemetry data
```
**To:**
```markdown
- **TimescaleDB isolation** — Tenant filtering via tenant_id column with application-level enforcement
```

---

## docs/ARCHITECTURE.md Updates

### Line 19 - Architecture diagram
**Change:**
```
IoT Devices ──► MQTT (1883) ──► ingest_iot ──► InfluxDB (telemetry)
```
**To:**
```
IoT Devices ──► MQTT (1883) ──► ingest_iot ──► TimescaleDB (telemetry)
```

### Line 44 - Port table
**Remove row:**
```markdown
| 8181 | InfluxDB | Time-series (internal) |
```

### Lines 52, 55 - Service descriptions
**Change from:**
```markdown
... batched InfluxDB writes. Multi-worker async pipeline processes ~2000 msg/sec per instance.
... Reads telemetry from InfluxDB to maintain `device_state`...
```
**To:**
```markdown
... batched TimescaleDB writes. Multi-worker async pipeline processes ~20,000 msg/sec per instance.
... Reads telemetry from TimescaleDB to maintain `device_state`...
```

### Line 60 - API description
**Change from:**
```markdown
- **`/api/v2/*`** — REST API with JWT Bearer auth, per-tenant rate limiting, dynamic InfluxDB telemetry queries
```
**To:**
```markdown
- **`/api/v2/*`** — REST API with JWT Bearer auth, per-tenant rate limiting, TimescaleDB telemetry queries
```

### Lines 126-130 - Data Stores section
**Replace InfluxDB section:**
```markdown
### InfluxDB 3 Core
Time-series telemetry store with per-tenant databases (`telemetry_{tenant_id}`):
- Heartbeat measurements (device presence)
- Telemetry measurements (all dynamic metrics: battery_pct, temp_c, pressure_psi, etc.)
```
**With:**
```markdown
### TimescaleDB (PostgreSQL Extension)
Time-series telemetry stored in a single `telemetry` hypertable:
- Automatic time-based partitioning (chunks)
- Compression policies for older data
- All metrics stored as JSONB in `metrics` column
- Tenant isolation via `tenant_id` column with application-level filtering
- Supports 20,000+ msg/sec with batched COPY inserts
```

### Lines 166-167 - Ingestion paths
**Change from:**
```markdown
Device → MQTT → ingest_iot → InfluxDB
Device → HTTP POST → ui_iot/ingest → InfluxDB
```
**To:**
```markdown
Device → MQTT → ingest_iot → TimescaleDB
Device → HTTP POST → ui_iot/ingest → TimescaleDB
```

### Lines 171-173 - Shared validation description
**Change from:**
```markdown
Both paths use shared validation (`services/shared/ingest_core.py`):
- DeviceAuthCache for credential caching
- InfluxBatchWriter for batched writes
- TokenBucket for per-device rate limiting
```
**To:**
```markdown
Both paths use shared validation (`services/shared/ingest_core.py`):
- DeviceAuthCache for credential caching
- TimescaleBatchWriter for batched writes (COPY for large batches, executemany for small)
- TokenBucket for per-device rate limiting
```

### Lines 177, 181 - Flow diagrams
**Change from:**
```markdown
Device → MQTT → ingest_iot → auth cache → validation → InfluxDB (batched writes)
...
ui_iot (REST API reads from InfluxDB + PG)
```
**To:**
```markdown
Device → MQTT → ingest_iot → auth cache → validation → TimescaleDB (batched writes)
...
ui_iot (REST API reads from TimescaleDB)
```

### Line 220 - Security architecture
**Change from:**
```markdown
4. **InfluxDB isolation**: Per-tenant databases for telemetry data
```
**To:**
```markdown
4. **TimescaleDB isolation**: Tenant filtering via tenant_id column with application-level enforcement
```

### Lines 255-256 - Operational knobs
**Change from:**
```markdown
- `INFLUX_BATCH_SIZE`: InfluxDB write batch size (default: 500)
- `INFLUX_FLUSH_INTERVAL_MS`: Max batch wait time (default: 1000)
```
**To:**
```markdown
- `TIMESCALE_BATCH_SIZE`: TimescaleDB write batch size (default: 500)
- `TIMESCALE_FLUSH_INTERVAL_MS`: Max batch wait time (default: 1000)
```

---

## docs/PROJECT_MAP.md Updates

### Lines 7, 12 - Network and flow diagrams
**Change from:**
```markdown
Devices → MQTT (:1883) → ingest_iot → InfluxDB (telemetry)
...
device → MQTT → ingest_iot (auth cache, batched writes) → InfluxDB (telemetry)
```
**To:**
```markdown
Devices → MQTT (:1883) → ingest_iot → TimescaleDB (telemetry)
...
device → MQTT → ingest_iot (auth cache, batched writes) → TimescaleDB (telemetry)
```

### Line 31 - Customer boundaries
**Change from:**
```markdown
- InfluxDB uses per-tenant databases for telemetry isolation
```
**To:**
```markdown
- TimescaleDB uses tenant_id column filtering for telemetry isolation
```

### Lines 44-45 - Data stores
**Change from:**
```markdown
- **PostgreSQL**: device_state, fleet_alert, alert_rules, integrations, integration_routes, delivery_jobs, delivery_attempts, delivery_log, quarantine_events, operator_audit_log, app_settings, rate_limits
- **InfluxDB 3 Core**: Per-tenant telemetry databases (heartbeat + dynamic metrics)
```
**To:**
```markdown
- **PostgreSQL + TimescaleDB**: All tables including telemetry hypertable. Core tables: device_state, fleet_alert, alert_rules, integrations, integration_routes, delivery_jobs, delivery_attempts, delivery_log, quarantine_events, operator_audit_log, app_settings, rate_limits, telemetry (hypertable), system_metrics (hypertable)
```

### Line 57 - Services table
**Change from:**
```markdown
| ingest_iot | iot-ingest | MQTT ingestion + InfluxDB writes |
```
**To:**
```markdown
| ingest_iot | iot-ingest | MQTT ingestion + TimescaleDB writes |
```

---

## Verification

```bash
# Check no InfluxDB references remain in documentation
cd /home/opsconductor/simcloud
grep -ri "influx" README.md docs/*.md | grep -v "cursor-prompts"

# Review changes
git diff README.md docs/ARCHITECTURE.md docs/PROJECT_MAP.md
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `README.md` |
| MODIFY | `docs/ARCHITECTURE.md` |
| MODIFY | `docs/PROJECT_MAP.md` |

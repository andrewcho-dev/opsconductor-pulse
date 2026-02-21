# 004: Documentation Updates

## Priority: HIGH

## Issues to Fix

### 1. SNMPv1: Document Accurately or Remove

**File:** `README.md`

**Problem:** Claims SNMPv1 support but `snmp_sender.py` only handles v2c and v3.

**Option A - Remove false claim:**
```markdown
## Features
...
- **SNMP trap delivery** to network management systems supporting SNMPv2c and SNMPv3
```

**Option B - Implement SNMPv1:** See separate implementation task.

---

### 2. Add Subscription System Documentation

**File:** `README.md`

**Add section after "Features":**
```markdown
## Subscription & Entitlement System

OpsConductor Pulse includes a comprehensive subscription management system:

### Subscription Types
- **MAIN** — Primary annual subscription with device limit
- **ADDON** — Additional capacity, coterminous with parent MAIN
- **TRIAL** — Short-term evaluation (default 14 days)
- **TEMPORARY** — Project or event-based subscriptions

### Subscription Lifecycle
```
TRIAL → ACTIVE → (renewal) → ACTIVE
                     ↓ (no payment)
                   GRACE (14 days)
                     ↓ (still no payment)
                   SUSPENDED (access blocked)
                     ↓ (90 days)
                   EXPIRED (data retained 1 year)
```

### Device Entitlements
- Each device assigned to exactly one subscription
- Device limits enforced at creation time
- Auto-provisioning respects subscription capacity
- Operators can reassign devices between subscriptions

### Customer API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /customer/subscriptions | List all subscriptions with summary |
| GET | /customer/subscriptions/{id} | Subscription detail with devices |
| GET | /customer/subscription/audit | Subscription audit history |
| POST | /customer/subscription/renew | Request renewal |

### Operator API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /operator/subscriptions | Create subscription |
| GET | /operator/subscriptions | List all subscriptions |
| GET | /operator/subscriptions/{id} | Subscription detail |
| PATCH | /operator/subscriptions/{id} | Update subscription |
| POST | /operator/devices/{id}/subscription | Assign device |
| GET | /operator/subscriptions/expiring | Expiring subscriptions |
| GET | /operator/subscriptions/summary | Platform summary |
```

---

### 3. Update db/README.md with All Migrations

**File:** `db/README.md`

**Replace migration table with complete list:**
```markdown
## Migrations

| # | File | Description |
|---|------|-------------|
| 000 | base_schema.sql | Core tables: device_registry, device_state, fleet_alert, alert_rules, quarantine |
| 001 | webhook_delivery_v1.sql | Delivery system: integrations, integration_routes, delivery_jobs |
| 002 | alert_rule_routes.sql | Alert rule to route mapping |
| 003 | delivery_attempts.sql | Delivery attempt tracking |
| 004 | enable_rls.sql | Row-level security policies |
| 005 | add_dispatch_id.sql | Dispatch tracking |
| 006 | tags_management.sql | Device tagging system |
| 007 | dispatcher_indexes.sql | Dispatcher performance indexes |
| 008 | operator_audit_log.sql | Operator audit logging |
| 009 | integration_types.sql | Integration type columns |
| 010 | webhook_enhancements.sql | Webhook improvements |
| 011 | mqtt_integration.sql | MQTT delivery support |
| 012 | snmp_integration.sql | SNMP trap delivery |
| 013 | email_integration.sql | Email delivery support |
| 014 | rate_limiting.sql | Per-device rate limiting |
| 015 | delivery_queue_indexes.sql | Queue performance |
| 016 | deprecate_raw_events.sql | Rename raw_events to deprecated |
| 017 | alert_rules_rls.sql | Alert rules RLS policies |
| 018 | tenants_table.sql | Multi-tenant support |
| 019 | remove_tenant_plan_fields.sql | Schema cleanup |
| 020 | enable_timescaledb.sql | TimescaleDB extension |
| 021 | telemetry_hypertable.sql | Telemetry hypertable |
| 022 | system_metrics_hypertable.sql | System metrics hypertable |
| 023 | timescale_policies.sql | Compression and retention |
| 024 | device_extended_attributes.sql | Device attributes, geocoding |
| 025 | fix_alert_rules_schema.sql | Alert rules column fixes |
| 026 | metric_catalog.sql | Metric catalog table |
| 027 | metric_normalization.sql | Metric normalization mappings |
| 028 | system_audit_log.sql | System-wide audit log |
| 029 | subscription_entitlements.sql | Subscription tables |
| 030 | multi_subscription.sql | Multi-subscription schema |
| 031 | migrate_subscription_data.sql | Data migration |
| 032 | remove_tenant_subscription.sql | Deprecation cleanup |
```

---

### 4. Update ARCHITECTURE.md for TimescaleDB

**File:** `docs/ARCHITECTURE.md`

**Replace InfluxDB section with:**
```markdown
### TimescaleDB (PostgreSQL Extension)

Time-series data is stored using TimescaleDB hypertables for automatic partitioning and compression:

**telemetry** — Device telemetry and heartbeats:
- Partitioned by time (automatic chunking)
- Compression enabled for data older than 7 days
- Retention policy: 90 days (configurable)
- Columns: `time`, `tenant_id`, `device_id`, `msg_type`, `metrics` (JSONB)
- Supports 20,000+ messages/second with batched COPY inserts

**system_metrics** — Platform monitoring:
- CPU, memory, disk, network metrics per service
- Used by System Dashboard
- Same compression/retention policies

**Query patterns:**
- Recent data: Standard SELECT with time range
- Aggregations: TimescaleDB `time_bucket()` for downsampling
- Metrics access: JSONB operators (`->`, `->>`, `?`)

**Migration from InfluxDB:**
Phase 30 migrated all time-series storage from InfluxDB to TimescaleDB for:
- Simplified operations (single database)
- Better integration with RLS
- Native PostgreSQL tooling
```

---

### 5. Add Metric Catalog Documentation

**File:** `docs/ARCHITECTURE.md`

**Add section:**
```markdown
### Metric Catalog & Normalization

The metric system provides consistent naming across different device types:

**metric_catalog** — Defines known metrics:
- `metric_name`: Internal name (e.g., `cpu_temp`)
- `display_name`: Human-readable (e.g., "CPU Temperature")
- `unit`: Measurement unit (e.g., "°C")
- `description`: Documentation

**normalized_metrics** — Unified metric definitions:
- Maps raw device metrics to normalized names
- Enables cross-device comparisons
- Supports metric aliasing

**metric_mappings** — Raw to normalized mapping:
- Per-device-type mappings
- Handles vendor-specific naming
- Automatic normalization in queries

**API Endpoints:**
- GET/POST/DELETE `/customer/metrics/catalog`
- GET/POST/PATCH/DELETE `/customer/normalized-metrics`
- GET/POST/PATCH/DELETE `/customer/metric-mappings`
```

---

### 6. Add Tenant Management API Documentation

**File:** `README.md`

**Add to Operator API section:**
```markdown
### Tenant Management (Operator)
| Method | Path | Description |
|--------|------|-------------|
| POST | /operator/tenants | Create tenant |
| GET | /operator/tenants | List all tenants |
| GET | /operator/tenants/{id} | Tenant details |
| PATCH | /operator/tenants/{id} | Update tenant |
| DELETE | /operator/tenants/{id} | Delete tenant |
| GET | /operator/tenants/stats/summary | Platform statistics |
| GET | /operator/tenants/{id}/stats | Tenant statistics |
| GET | /operator/tenants/{id}/devices | Tenant devices |
```

---

### 7. Add Device Management API Documentation

**File:** `README.md`

**Add to Customer API section:**
```markdown
### Device Management (Customer)
| Method | Path | Description |
|--------|------|-------------|
| GET | /customer/devices | List devices with pagination |
| POST | /customer/devices | Register new device |
| GET | /customer/devices/{id} | Device details |
| PATCH | /customer/devices/{id} | Update device attributes |
| DELETE | /customer/devices/{id} | Deactivate device |
| GET | /customer/devices/{id}/tags | Get device tags |
| PUT | /customer/devices/{id}/tags | Replace device tags |
| POST | /customer/devices/{id}/tags | Add tags |
| DELETE | /customer/devices/{id}/tags | Remove tags |
| GET | /customer/tags | List all tenant tags |
| GET | /customer/geocode | Geocode address |
```

---

### 8. Update Cursor Prompts README

**File:** `docs/cursor-prompts/README.md`

**Add missing phases:**
```markdown
## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1-22 | Core platform | Complete |
| 23 | HTTP REST Ingestion | Complete |
| 24 | Demo Data Generator | Complete |
| 25 | Dashboard Visualizations | Complete |
| 26 | Device Simulator | Complete |
| 27 | Theme Switcher | Complete |
| 28 | Tenant Management | Complete |
| 29 | Operator System Dashboard | Complete |
| 30 | TimescaleDB Migration | Complete |
| 31 | Subscription Entitlements | Complete |
| 32 | Multi-Subscription | Complete |
| 33 | Subscription Follow-up | Complete |
| 34 | Code Review Remediation | In Progress |
```

---

### 9. Document Environment Variables

**File:** `README.md`

**Add section:**
```markdown
## Environment Variables

### Database
| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://iot:iot_dev@postgres:5432/iotcloud | PostgreSQL connection |
| TIMESCALE_BATCH_SIZE | 1000 | Telemetry batch insert size |
| TIMESCALE_FLUSH_INTERVAL_MS | 1000 | Batch flush interval |

### Authentication
| Variable | Default | Description |
|----------|---------|-------------|
| KEYCLOAK_URL | https://localhost | Keycloak server URL |
| KEYCLOAK_REALM | iotcloud | Keycloak realm |
| AUTH_CACHE_TTL_SECONDS | 300 | JWKS cache TTL |

### Ingestion
| Variable | Default | Description |
|----------|---------|-------------|
| INGEST_WORKER_COUNT | 4 | Parallel ingest workers |
| INGEST_QUEUE_SIZE | 10000 | Message queue size |
| API_RATE_LIMIT | 100 | Requests per window |
| API_RATE_WINDOW_SECONDS | 60 | Rate limit window |

### WebSocket
| Variable | Default | Description |
|----------|---------|-------------|
| WS_POLL_SECONDS | 5 | WebSocket poll interval |

### CORS
| Variable | Default | Description |
|----------|---------|-------------|
| CORS_ORIGINS | * | Allowed origins (comma-separated) |

### Notifications
| Variable | Default | Description |
|----------|---------|-------------|
| NOTIFICATION_WEBHOOK_URL | (none) | External notification webhook |
| WORKER_INTERVAL_SECONDS | 3600 | Subscription worker interval |
```

---

### 10. Mark Deprecated Features

**File:** `docs/PROJECT_MAP.md`

**Update data stores section:**
```markdown
## Data Stores

### Active
- **PostgreSQL + TimescaleDB** — Primary database with time-series extension
- **subscriptions** — Multi-subscription entitlements
- **subscription_audit** — Subscription event history

### Deprecated
- ~~InfluxDB~~ — Removed in Phase 30, replaced by TimescaleDB
- ~~tenant_subscription~~ — Replaced by `subscriptions` table in Phase 32
- ~~raw_events~~ — Renamed to `_deprecated_raw_events` in Phase 16
```

---

## Verification

After updates:
```bash
# Check all markdown renders correctly
npx markdownlint docs/**/*.md README.md

# Verify no broken internal links
grep -r "\[.*\](.*\.md)" docs/ | while read line; do
  file=$(echo "$line" | sed 's/.*(\(.*\.md\)).*/\1/')
  if [[ ! -f "docs/$file" && ! -f "$file" ]]; then
    echo "Broken link: $line"
  fi
done
```

## Files Changed

- `README.md`
- `db/README.md`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_MAP.md`
- `docs/cursor-prompts/README.md`
- `docs/INTEGRATIONS_AND_DELIVERY.md`

# OpsConductor-Pulse Architecture

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed devices. It provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards for IoT fleet management.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  IoT Devices ──► MQTT ──► ingest_iot ──► raw_events                         │
│                                              │                               │
│  Keycloak ◄──────────────────────────────────┼───► ui_iot (Customer/Operator)│
│                                              │                               │
│  provision_api ◄── Admin (X-Admin-Key)       ▼                               │
│                                        evaluator_iot                         │
│                                              │                               │
│                                              ▼                               │
│                                    device_state + fleet_alert                │
│                                              │                               │
│                                              ▼                               │
│                                         dispatcher                           │
│                                              │                               │
│                                              ▼                               │
│                                      delivery_worker                         │
│                                         │      │                             │
│                                         ▼      ▼                             │
│                              Webhook Endpoints  SNMP Managers                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Services and Responsibilities

### services/ingest_iot
Device ingress, authentication, validation, and quarantine. Handles MQTT/HTTP device connections, validates tokens, enforces rate limits, and separates accepted events from rejected/quarantined events.

### services/evaluator_iot
Heartbeat tracking, state management, and alert generation. Processes accepted raw_events to maintain device_state, detects stale devices, and generates fleet_alert records for operational issues.

### services/ui_iot
Customer and operator dashboards with Keycloak authentication. Provides:
- **Customer plane**: Tenant-scoped device views, alert monitoring, integration management
- **Operator plane**: Cross-tenant views with audit logging

### services/provision_api
Admin and device provisioning APIs. Handles device registration, activation code generation, token management, and administrative operations protected by X-Admin-Key.

### services/dispatcher
Alert-to-delivery job dispatcher. Polls fleet_alert for open alerts, matches them against integration_routes, and creates delivery_jobs for the worker.

### services/delivery_worker
Alert delivery via webhook and SNMP. Processes delivery_jobs with retry logic and exponential backoff. Supports:
- **Webhooks**: HTTP POST with JSON payload
- **SNMP**: v2c and v3 trap delivery

### simulator/device_sim_iot
Simulation only. Generates realistic device telemetry and heartbeat messages for testing and development. Never referenced in production logic.

## Authentication Model

OpsConductor-Pulse uses Keycloak as the identity provider with JWT tokens.

### User Roles

| Role | Description | Access |
|------|-------------|--------|
| `customer_viewer` | Read-only customer access | View devices, alerts, delivery status |
| `customer_admin` | Full customer access | Above + manage integrations, routes |
| `operator` | Cross-tenant operator access | All customer data, audited |
| `operator_admin` | Operator with admin functions | Above + system settings |

### JWT Claims

```json
{
  "iss": "https://auth.example.com/realms/pulse",
  "sub": "user-uuid",
  "tenant_id": "customer-abc",
  "role": "customer_admin"
}
```

## Data Model Overview

### raw_events
Central event store with `accepted` boolean flag. Only `accepted=true` events drive device_state updates. Contains tenant_id, device_id, msg_type, and full payload.

### quarantine_events
Rejected events that failed validation. Stores rejection reason and original payload for debugging. Never affects device state.

### device_state
Current device status derived from accepted raw_events. Tenant-scoped with ONLINE/STALE status, last seen timestamps, and latest telemetry metrics.

### fleet_alert
Generated alerts for operational issues. Tenant-scoped with severity, confidence, and deduplication via fingerprint.

### integrations
Customer-configured delivery destinations. Supports webhook and SNMP types with tenant isolation.

### integration_routes
Rules for matching alerts to integrations. Filter by alert_type, severity, site, device prefix.

### delivery_jobs
Queued delivery attempts with status tracking and retry logic.

### delivery_attempts
History of individual delivery attempts with timing and error details.

## Core Flows

### Device Telemetry/Heartbeat Flow
```
Device → MQTT → ingest_iot → validation → accepted=true → raw_events
                                               ↓
                                       evaluator_iot → device_state/fleet_alert
                                               ↓
                                               ui_iot (read-only)
```

### Alert Delivery Flow
```
fleet_alert → dispatcher → route match → delivery_job
                                              ↓
                                      delivery_worker
                                         ↓      ↓
                              webhook POST    SNMP trap
                                         ↓      ↓
                              delivery_attempts (logged)
```

### Rejection/Quarantine Flow
```
Device → MQTT → ingest_iot → validation failure → quarantine_events
                                               ↓
                                       quarantine_counters_minute
                                               ↓
                                               ui_iot (ops dashboard)
```

### Provisioning Flow
```
Operator → provision_api (X-Admin-Key) → create device → activation_code
Device → provision_api → activation_code → provision_token
Device → ingest_iot → provision_token validation → accepted telemetry
```

## Security Architecture

### Tenant Isolation

1. **JWT-based identity**: tenant_id extracted from validated JWT claims only
2. **Application enforcement**: All queries include tenant_id in WHERE clause
3. **RLS defense-in-depth**: Database row-level security as backup layer
4. **Audit logging**: All operator cross-tenant access is logged

### RLS Configuration

```sql
-- Customer connection sets tenant context
SET LOCAL app.tenant_id = 'tenant-abc';

-- RLS policies restrict access
CREATE POLICY device_state_tenant ON device_state
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));
```

### SSRF Prevention

Customer-provided URLs (webhooks, SNMP destinations) are validated:
- Private IP ranges blocked (10.x, 172.16.x, 192.168.x)
- Loopback addresses blocked
- Cloud metadata endpoints blocked
- DNS resolution validated

## Operational Knobs

### MODE DEV/PROD
- PROD: Debug storage disabled, rejects not stored/mirrored, HTTPS required for webhooks
- DEV: Full debugging enabled, rejects can be stored for analysis

### Delivery Configuration
- `WORKER_MAX_ATTEMPTS`: Maximum retry attempts (default: 5)
- `WORKER_BACKOFF_BASE_SECONDS`: Initial retry delay (default: 30)
- `WORKER_TIMEOUT_SECONDS`: HTTP/SNMP timeout (default: 30)

### Rate Limiting
- Per-device token bucket rate limiting
- Per-tenant test delivery limits (5/minute)

## Explicit Non-Goals (Current Version)

- Custom protocol adapters via plugin system
- Multi-region deployment
- Advanced billing and metering
- External secret management (HashiCorp Vault)

# OpsConductor-Pulse Architecture

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed devices. It provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards for IoT fleet management.

## Services and Responsibilities

### services/ingest_iot
Device ingress, authentication, validation, and quarantine. Handles MQTT/HTTP device connections, validates tokens, enforces rate limits, and separates accepted events from rejected/quarantined events.

### services/evaluator_iot
Heartbeat tracking, state management, and alert generation. Processes accepted raw_events to maintain device_state, detects stale devices, and generates fleet_alert records for operational issues.

### services/ui_iot
Read-only dashboards for operators. Provides system health views, device status, alert monitoring, and quarantine analytics. No device write capabilities.

### services/provision_api
Admin and device provisioning APIs. Handles device registration, activation code generation, token management, and administrative operations protected by X-Admin-Key.

### simulator/device_sim_iot
Simulation only. Generates realistic device telemetry and heartbeat messages for testing and development. Never referenced in production logic.

## Data Model Overview

### raw_events
Central event store with `accepted` boolean flag. Only `accepted=true` events drive device_state updates. Contains tenant_id, device_id, msg_type, and full payload.

### quarantine_events
Rejected events that failed validation. Stores rejection reason and original payload for debugging. Never affects device state.

### quarantine_counters_minute
Per-tenant, per-reason rate limiting counters. Used for operational monitoring and rate limiting enforcement.

### device_state
Current device status derived from accepted raw_events. Tenant-scoped with ONLINE/STALE status, last seen timestamps, and latest telemetry metrics.

### fleet_alert
Generated alerts for operational issues. Tenant-scoped with severity, confidence, and deduplication via fingerprint.

### app_settings
Runtime configuration knobs. Controls MODE (DEV/PROD), rejection storage policies, and rate limiting parameters.

## Core Flows

### Device Telemetry/Heartbeat Flow
```
Device → MQTT → ingest_iot → validation → accepted=true → raw_events
                                                ↓
                                        evaluator_iot → device_state/fleet_alert
                                                ↓
                                                ui_iot (read-only)
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

## Operational Knobs

### MODE DEV/PROD
- PROD: Debug storage disabled, rejects not stored/mirrored
- DEV: Full debugging enabled, rejects can be stored for analysis

### STORE_REJECTS / MIRROR_REJECTS_TO_RAW
- Controls whether rejected payloads are persisted
- In PROD mode, both are forced to disabled for security

### Rate Limiting Counters
- Per-device token bucket rate limiting
- Configurable RPS and burst parameters
- Quarantine counters provide visibility into rejection patterns

## Explicit Non-Goals (Current Version)

- Role-based access control (RBAC) within customer planes
- Single sign-on (SSO) integration
- Alert delivery workers and integrations
- Multi-region deployment
- Advanced billing and metering

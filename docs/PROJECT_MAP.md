# OpsConductor-Pulse – Project Map

## Device Flow
device → MQTT/HTTP → ingest_iot → InfluxDB (telemetry)
→ evaluator_iot → device_state / alerts
→ ui_iot (read-only, reads telemetry from InfluxDB)

## Admin Flow
admin → provision_api → activation_code
device → activate → provision_token

## Customer Boundaries
- tenant_id is the isolation boundary
- customers only see their tenant
- ops/admin sees all tenants
- InfluxDB uses per-tenant databases for telemetry isolation

## Alert Outputs
- Webhooks (HTTP POST with JSON payload)
- SNMP traps (v2c and v3)
- Email (SMTP with HTML/text templates)
- MQTT (publish to customer-configured topics)

## Data Stores
- **PostgreSQL**: Transactional data (device_state, fleet_alert, integrations, delivery_jobs, quarantine_events)
- **InfluxDB 3 Core**: Time-series telemetry (heartbeat, telemetry per tenant database)

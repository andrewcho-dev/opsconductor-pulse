# OpsConductor-Pulse – Project Map

## Device Flow
device → MQTT/HTTP → ingest_iot → raw_events
→ evaluator_iot → device_state / alerts
→ ui_iot (read-only)

## Admin Flow
admin → provision_api → activation_code
device → activate → provision_token

## Customer Boundaries
- tenant_id is the isolation boundary
- customers only see their tenant
- ops/admin sees all tenants

## Alert Outputs (future)
- SNMP traps
- Webhooks
- Email / SMS

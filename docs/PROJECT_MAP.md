# OpsConductor-Pulse – Project Map

## Network Topology
```
Browser → Caddy (HTTPS :443) → ui_iot (React SPA + JSON APIs)
                               → Keycloak (OIDC auth)
Devices → MQTT (:1883) → ingest_iot → TimescaleDB (telemetry)
Admin → provision_api (:8081)
```

## Device Flow
device → MQTT → ingest_iot (auth cache, batched writes) → TimescaleDB (telemetry)
→ evaluator_iot → device_state / fleet_alert (NO_HEARTBEAT + THRESHOLD)
→ dispatcher → delivery_worker → webhook / SNMP / email / MQTT

## Frontend
React SPA (Vite + TypeScript + TailwindCSS + shadcn/ui)
- Customer: Dashboard, Devices, Device Detail (ECharts gauges + uPlot charts), Alerts, Alert Rules, Integrations (4 types)
- Operator: Overview, All Devices, Audit Log, Settings
- Auth: keycloak-js (browser-native OIDC/PKCE)
- State: TanStack Query (REST) + Zustand (WebSocket live data)

## Admin Flow
admin → provision_api (X-Admin-Key) → activation_code
device → activate → provision_token

## Customer Boundaries
- tenant_id is the isolation boundary (JWT claim)
- customers only see their tenant (RLS via pulse_app role)
- operators see all tenants (BYPASSRLS via pulse_operator role, audited)
- TimescaleDB uses tenant_id column filtering for telemetry isolation

## Alert Types
- NO_HEARTBEAT — device missed heartbeat window
- THRESHOLD — customer-defined rule violation (GT/LT/GTE/LTE on any metric)

## Alert Outputs
- Webhooks (HTTP POST with JSON payload)
- SNMP traps (v2c and v3)
- Email (SMTP with HTML/text templates)
- MQTT (publish to customer-configured topics)

## Data Stores
- **PostgreSQL + TimescaleDB**: All tables including telemetry hypertable. Core tables: device_state, fleet_alert, alert_rules, integrations, integration_routes, delivery_jobs, delivery_attempts, delivery_log, quarantine_events, operator_audit_log, app_settings, rate_limits, telemetry (hypertable), system_metrics (hypertable)

## API Layers
- `/api/v2/*` — REST API + WebSocket (customer-scoped, JWT Bearer)
- `/customer/*` — Customer JSON APIs (integration CRUD, alert rules, devices)
- `/operator/*` — Operator JSON APIs (cross-tenant, audited)
- `/api/admin/*` — Provisioning (X-Admin-Key)

## Key Services
| Service | Container | Purpose |
|---------|-----------|---------|
| caddy | iot-caddy | HTTPS reverse proxy |
| ingest_iot | iot-ingest | MQTT ingestion + TimescaleDB writes |
| evaluator_iot | iot-evaluator | State tracking + alert generation |
| ui_iot | iot-ui | FastAPI backend + SPA serving |
| provision_api | iot-api | Device provisioning |
| dispatcher | iot-dispatcher | Alert → delivery job routing |
| delivery_worker | iot-delivery-worker | Webhook/SNMP/email/MQTT delivery |
| keycloak | pulse-keycloak | OIDC identity provider |
| device_sim_iot | iot-device-sim | 25-device simulator |

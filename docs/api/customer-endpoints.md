---
last-verified: 2026-02-19
sources:
  - services/ui_iot/routes/customer.py
  - services/ui_iot/routes/alerts.py
  - services/ui_iot/routes/devices.py
  - services/ui_iot/routes/sensors.py
  - services/ui_iot/routes/ingest.py
  - services/ui_iot/routes/metrics.py
  - services/ui_iot/routes/exports.py
  - services/ui_iot/routes/escalation.py
  - services/ui_iot/routes/notifications.py
  - services/ui_iot/routes/oncall.py
  - services/ui_iot/routes/jobs.py
  - services/ui_iot/routes/ota.py
  - services/ui_iot/routes/dashboards.py
  - services/ui_iot/routes/users.py
  - services/ui_iot/routes/roles.py
  - services/ui_iot/routes/preferences.py
  - services/ui_iot/routes/billing.py
  - services/ui_iot/routes/carrier.py
  - services/ui_iot/routes/templates.py
  - services/ui_iot/routes/organization.py
  - services/ui_iot/routes/certificates.py
  - services/ui_iot/routes/analytics.py
  - services/ui_iot/routes/message_routing.py
  - services/ui_iot/routes/operator.py
  - services/ingest_iot/ingest.py
phases: [23, 96, 122, 123, 125, 126, 127, 134, 142, 157, 158, 166, 167, 168, 169, 170, 171, 172, 173]
---

# Customer API Endpoints

> Tenant-scoped REST API for customer users.

## Auth

All customer endpoints require JWT authentication via:

- `Authorization: Bearer <token>` header, or
- `pulse_session` cookie (UI session)

Tenant scope comes from the token's organization membership.

In examples below:

```bash
BASE="https://localhost"
H_AUTH=(-H "Authorization: Bearer $TOKEN" --insecure)
```

## Fleet & Devices

Base prefix: `/api/v1/customer`

- `POST /api/v1/customer/devices` — create device
  - Example: `curl -s "${H_AUTH[@]}" -X POST "$BASE/api/v1/customer/devices" -H "Content-Type: application/json" -d '{"device_id":"dev-001","site_id":"site-1"}'`
  - Body supports optional `template_id` and `parent_device_id`
  - When `template_id` is provided, required template metrics are auto-created as `device_sensors` and transport defaults may auto-create a `device_transports` row.
- `GET /api/v1/customer/devices` — list devices
  - Example: `curl -s "${H_AUTH[@]}" "$BASE/api/v1/customer/devices?limit=50&offset=0"`
- `GET /api/v1/customer/devices/summary` — fleet summary
  - Example: `curl -s "${H_AUTH[@]}" "$BASE/api/v1/customer/devices/summary"`
- `GET /api/v1/customer/devices/{device_id}` — device detail
  - Example: `curl -s "${H_AUTH[@]}" "$BASE/api/v1/customer/devices/dev-001"`
- `PATCH /api/v1/customer/devices/{device_id}` — update device (name/site/tags/etc.)
  - Example: `curl -s "${H_AUTH[@]}" -X PATCH "$BASE/api/v1/customer/devices/dev-001" -H "Content-Type: application/json" -d '{"name":"New Name"}'`
  - Supports updating `template_id` (required sensors from the new template are added; existing sensors are not removed automatically).
- `PATCH /api/v1/customer/devices/{device_id}/decommission` — decommission device
  - Example: `curl -s "${H_AUTH[@]}" -X PATCH "$BASE/api/v1/customer/devices/dev-001/decommission" -H "Content-Type: application/json" -d '{}'`
- `DELETE /api/v1/customer/devices/{device_id}` — delete device (if supported)
  - Example: `curl -s "${H_AUTH[@]}" -X DELETE "$BASE/api/v1/customer/devices/dev-001"`

Tokens:

- `GET /api/v1/customer/devices/{device_id}/tokens` — list API tokens
- `POST /api/v1/customer/devices/{device_id}/tokens/rotate` — rotate token
- `DELETE /api/v1/customer/devices/{device_id}/tokens/{token_id}` — revoke token

Example:

```bash
curl -s "${H_AUTH[@]}" "$BASE/api/v1/customer/devices/dev-001/tokens"
```

Telemetry and twin:

- `GET /api/v1/customer/devices/{device_id}/telemetry`
- `GET /api/v1/customer/devices/{device_id}/telemetry/latest`
- `GET /api/v1/customer/devices/{device_id}/telemetry/metrics` — list available chart metrics (from `device_sensors`)
- `GET /api/v1/customer/devices/{device_id}/telemetry/history`
  - Response includes sensor metadata (`unit`, `min_range`, `max_range`, `precision_digits`) when available.
- `GET /api/v1/customer/devices/{device_id}/telemetry/export`
- `GET /api/v1/customer/devices/{device_id}/twin`
- `PATCH /api/v1/customer/devices/{device_id}/twin/desired`
- `GET /api/v1/customer/devices/{device_id}/twin/delta`

Example:

```bash
curl -s "${H_AUTH[@]}" "$BASE/api/v1/customer/devices/dev-001/telemetry/latest"
```

Commands:

- `POST /api/v1/customer/devices/{device_id}/commands` — send a command
- `GET /api/v1/customer/devices/{device_id}/commands` — list commands

Tags and groups:

- `GET /api/v1/customer/devices/{device_id}/tags`
- `PUT /api/v1/customer/devices/{device_id}/tags`
- `POST /api/v1/customer/devices/{device_id}/tags/{tag}`
- `DELETE /api/v1/customer/devices/{device_id}/tags/{tag}`
- `GET /api/v1/customer/tags`
- `GET /api/v1/customer/device-groups`
- `POST /api/v1/customer/device-groups`
- `PATCH /api/v1/customer/device-groups/{group_id}`
- `DELETE /api/v1/customer/device-groups/{group_id}`
- `GET /api/v1/customer/device-groups/{group_id}/devices`
- `PUT /api/v1/customer/device-groups/{group_id}/devices/{device_id}`
- `DELETE /api/v1/customer/device-groups/{group_id}/devices/{device_id}`

Maintenance windows:

- `GET /api/v1/customer/maintenance-windows`
- `POST /api/v1/customer/maintenance-windows`
- `PATCH /api/v1/customer/maintenance-windows/{window_id}`
- `DELETE /api/v1/customer/maintenance-windows/{window_id}`

Device modules:

- `GET /api/v1/customer/devices/{device_id}/modules`
- `POST /api/v1/customer/devices/{device_id}/modules`
- `PUT /api/v1/customer/devices/{device_id}/modules/{module_id}`
- `DELETE /api/v1/customer/devices/{device_id}/modules/{module_id}` (soft delete: marks removed and deactivates linked sensors)

Device sensors (restructured; source = required|optional|unmodeled):

- `GET /api/v1/customer/devices/{device_id}/sensors`
- `POST /api/v1/customer/devices/{device_id}/sensors`
- `PUT /api/v1/customer/devices/{device_id}/sensors/{sensor_id}`
- `DELETE /api/v1/customer/devices/{device_id}/sensors/{sensor_id}` (cannot delete `source=required`; deactivate instead)
- Fleet-wide list (backward compat): `GET /api/v1/customer/sensors`

Device transports (replaces legacy device_connections):

- `GET /api/v1/customer/devices/{device_id}/transports`
- `POST /api/v1/customer/devices/{device_id}/transports`
- `PUT /api/v1/customer/devices/{device_id}/transports/{transport_id}`
- `DELETE /api/v1/customer/devices/{device_id}/transports/{transport_id}`

Deprecated:

- `GET/PUT/DELETE /api/v1/customer/devices/{device_id}/connection` (deprecated; successor is `/transports`)

## Device Templates

Base prefix: `/api/v1/customer`

- `GET /api/v1/customer/templates` — list templates visible to tenant (system + own)
  - Query: `category`, `source`, `search`
- `GET /api/v1/customer/templates/{template_id}` — get full template with sub-resources
- `POST /api/v1/customer/templates` — create tenant template
- `PUT /api/v1/customer/templates/{template_id}` — update own template (403 if locked/system)
- `DELETE /api/v1/customer/templates/{template_id}` — delete own template (409 if devices using it)
- `POST /api/v1/customer/templates/{template_id}/clone` — clone a template into a tenant-owned copy

Sub-resources:

- Metrics:
  - `POST /api/v1/customer/templates/{template_id}/metrics`
  - `PUT /api/v1/customer/templates/{template_id}/metrics/{metric_id}`
  - `DELETE /api/v1/customer/templates/{template_id}/metrics/{metric_id}`
- Commands:
  - `POST /api/v1/customer/templates/{template_id}/commands`
  - `PUT /api/v1/customer/templates/{template_id}/commands/{command_id}`
  - `DELETE /api/v1/customer/templates/{template_id}/commands/{command_id}`
- Slots:
  - `POST /api/v1/customer/templates/{template_id}/slots`
  - `PUT /api/v1/customer/templates/{template_id}/slots/{slot_id}`
  - `DELETE /api/v1/customer/templates/{template_id}/slots/{slot_id}`

## Carrier

Base prefix: `/api/v1/customer`

Carrier integrations:

- `GET /api/v1/customer/carrier/integrations`
- `POST /api/v1/customer/carrier/integrations` (permission: `carrier.integrations.write`, feature gate: `carrier_self_service`)
- `PUT /api/v1/customer/carrier/integrations/{integration_id}` (permission: `carrier.integrations.write`, feature gate: `carrier_self_service`)
- `DELETE /api/v1/customer/carrier/integrations/{integration_id}` (permission: `carrier.integrations.write`, feature gate: `carrier_self_service`)

Device carrier operations:

- `GET /api/v1/customer/devices/{device_id}/carrier/status`
- `GET /api/v1/customer/devices/{device_id}/carrier/usage`
- `GET /api/v1/customer/devices/{device_id}/carrier/diagnostics`
- `POST /api/v1/customer/devices/{device_id}/carrier/actions/{action}` (permission: `carrier.actions.execute`)
- `POST /api/v1/customer/devices/{device_id}/carrier/link` (permission: `carrier.links.write`)

### SIM Provisioning

`POST /api/v1/customer/devices/{device_id}/carrier/provision`

Claim a new SIM from the carrier and link it to a device.

- Permission: `carrier.links.write`
- Feature gate: `carrier_self_service`
- Body: `{ carrier_integration_id: int, iccid: string, plan_id?: int }`
- Response: `{ provisioned: bool, device_id, carrier_device_id, iccid, claim_result }`

### Plan Discovery

`GET /api/v1/customer/carrier/integrations/{integration_id}/plans`

List available data plans from the carrier.

- Permission: none (read-only)
- Response: `{ plans: [{ id, name, ... }], carrier_name }`
- Note: returns empty array for carriers that don't support plan listing (e.g., 1NCE).

## Operator — Carrier Management

Operator endpoints are cross-tenant (RLS bypass via `operator_connection()`), and all access is audited via `log_operator_access()`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/operator/carrier-integrations` | Operator | List all integrations cross-tenant. Query: `tenant_id`, `carrier_name`, `limit`, `offset` |
| POST | `/api/v1/operator/carrier-integrations` | Operator Admin | Create integration for a tenant. Body requires `tenant_id` |
| PUT | `/api/v1/operator/carrier-integrations/{id}` | Operator Admin | Update any integration |
| DELETE | `/api/v1/operator/carrier-integrations/{id}` | Operator Admin | Delete integration + unlink devices |

## Alerts

Base prefix: `/api/v1/customer`

- `GET /api/v1/customer/alerts` — list alerts
- `GET /api/v1/customer/alerts/{alert_id}` — alert detail
- `PATCH /api/v1/customer/alerts/{alert_id}/acknowledge`
- `PATCH /api/v1/customer/alerts/{alert_id}/close`
- `PATCH /api/v1/customer/alerts/{alert_id}/silence`
- `GET /api/v1/customer/alerts/trend`

Example:

```bash
curl -s "${H_AUTH[@]}" "$BASE/api/v1/customer/alerts?status=OPEN&limit=50&offset=0"
```

## Alert Rules

- `GET /api/v1/customer/alert-rules`
- `GET /api/v1/customer/alert-rules/{rule_id}`
- `POST /api/v1/customer/alert-rules`
- `PATCH /api/v1/customer/alert-rules/{rule_id}`
- `DELETE /api/v1/customer/alert-rules/{rule_id}`

Templates:

- `GET /api/v1/customer/alert-rule-templates`
- `POST /api/v1/customer/alert-rule-templates/apply`

Digest settings:

- `GET /api/v1/customer/alert-digest-settings`
- `PUT /api/v1/customer/alert-digest-settings`

## Escalation Policies

- `GET /api/v1/customer/escalation-policies`
- `POST /api/v1/customer/escalation-policies`
- `GET /api/v1/customer/escalation-policies/{policy_id}`
- `PUT /api/v1/customer/escalation-policies/{policy_id}`
- `DELETE /api/v1/customer/escalation-policies/{policy_id}`

## Notification Channels & Routing

Channels:

- `GET /api/v1/customer/notification-channels`
- `POST /api/v1/customer/notification-channels`
- `GET /api/v1/customer/notification-channels/{channel_id}`
- `PUT /api/v1/customer/notification-channels/{channel_id}`
- `DELETE /api/v1/customer/notification-channels/{channel_id}`
- `POST /api/v1/customer/notification-channels/{channel_id}/test`

Routing rules:

- `GET /api/v1/customer/notification-routing-rules`
- `POST /api/v1/customer/notification-routing-rules`
- `PUT /api/v1/customer/notification-routing-rules/{rule_id}`
- `DELETE /api/v1/customer/notification-routing-rules/{rule_id}`

Jobs/log:

- `GET /api/v1/customer/notification-jobs`

## On-Call Schedules

- `GET /api/v1/customer/oncall-schedules`
- `POST /api/v1/customer/oncall-schedules`
- `GET /api/v1/customer/oncall-schedules/{schedule_id}`
- `PUT /api/v1/customer/oncall-schedules/{schedule_id}`
- `DELETE /api/v1/customer/oncall-schedules/{schedule_id}`

Layers:

- `POST /api/v1/customer/oncall-schedules/{schedule_id}/layers`
- `PUT /api/v1/customer/oncall-schedules/{schedule_id}/layers/{layer_id}`
- `DELETE /api/v1/customer/oncall-schedules/{schedule_id}/layers/{layer_id}`

Overrides:

- `GET /api/v1/customer/oncall-schedules/{schedule_id}/overrides`
- `POST /api/v1/customer/oncall-schedules/{schedule_id}/overrides`
- `DELETE /api/v1/customer/oncall-schedules/{schedule_id}/overrides/{override_id}`

Views:

- `GET /api/v1/customer/oncall-schedules/{schedule_id}/current`
- `GET /api/v1/customer/oncall-schedules/{schedule_id}/timeline`

## IoT Jobs & Commands

- `POST /api/v1/customer/jobs`
- `GET /api/v1/customer/jobs`
- `GET /api/v1/customer/jobs/{job_id}`
- `DELETE /api/v1/customer/jobs/{job_id}`

## OTA Firmware

- `GET /api/v1/customer/firmware`
- `POST /api/v1/customer/firmware`
- `GET /api/v1/customer/ota/campaigns`
- `POST /api/v1/customer/ota/campaigns`
- `GET /api/v1/customer/ota/campaigns/{campaign_id}`
- `POST /api/v1/customer/ota/campaigns/{campaign_id}/start`
- `POST /api/v1/customer/ota/campaigns/{campaign_id}/pause`
- `POST /api/v1/customer/ota/campaigns/{campaign_id}/abort`
- `GET /api/v1/customer/ota/campaigns/{campaign_id}/devices`

## Dashboards

Base prefix: `/api/v1/customer/dashboards`

- `GET /api/v1/customer/dashboards` — list dashboards
- `POST /api/v1/customer/dashboards` — create dashboard
- `GET /api/v1/customer/dashboards/{dashboard_id}` — get dashboard
- `PUT /api/v1/customer/dashboards/{dashboard_id}` — update dashboard
- `DELETE /api/v1/customer/dashboards/{dashboard_id}` — delete dashboard
- `PUT /api/v1/customer/dashboards/{dashboard_id}/share` — share settings
- `PUT /api/v1/customer/dashboards/{dashboard_id}/layout` — update layout
- `POST /api/v1/customer/dashboards/{dashboard_id}/widgets` — add widget
- `PUT /api/v1/customer/dashboards/{dashboard_id}/widgets/{widget_id}` — update widget
- `DELETE /api/v1/customer/dashboards/{dashboard_id}/widgets/{widget_id}` — delete widget
- `POST /api/v1/customer/dashboards/bootstrap` — create default dashboards

## Reports & Exports

Exports:

- `POST /api/v1/customer/exports` — create export job (202 accepted)
- `GET /api/v1/customer/exports` — list export jobs
- `GET /api/v1/customer/exports/{export_id}` — export job status/detail
- `GET /api/v1/customer/exports/{export_id}/download` — download export

Quick export helpers:

- `GET /api/v1/customer/export/devices`
- `GET /api/v1/customer/export/alerts`

Reports:

- `GET /api/v1/customer/reports/sla-summary`
- `GET /api/v1/customer/reports/runs`

Audit/legacy delivery status:

- `GET /api/v1/customer/audit-log`
- `GET /api/v1/customer/delivery-status`
- `GET /api/v1/customer/delivery-jobs`
- `GET /api/v1/customer/delivery-jobs/{job_id}/attempts`

## Billing & Subscriptions

Billing base prefix: `/api/v1/customer/billing`

- `GET /api/v1/customer/billing/config`
- `GET /api/v1/customer/billing/entitlements`
- `POST /api/v1/customer/billing/checkout-session`
- `POST /api/v1/customer/billing/portal-session`
- `POST /api/v1/customer/billing/addon-checkout`
- `GET /api/v1/customer/billing/status`
- `GET /api/v1/customer/billing/subscriptions`

Subscription views base prefix: `/api/v1/customer`

- `GET /api/v1/customer/subscriptions`
- `GET /api/v1/customer/subscriptions/{subscription_id}`
- `GET /api/v1/customer/subscription/audit`
- `POST /api/v1/customer/subscription/renew`

## Certificates

- `GET /api/v1/customer/certificates`
- `POST /api/v1/customer/certificates`
- `GET /api/v1/customer/certificates/{cert_id}`
- `POST /api/v1/customer/certificates/{cert_id}/revoke`
- `GET /api/v1/customer/ca-bundle`
- `GET /api/v1/customer/crl`
- `POST /api/v1/customer/devices/{device_id}/certificates/generate`
- `POST /api/v1/customer/devices/{device_id}/certificates/rotate`

## User Preferences

- `GET /api/v1/customer/preferences`
- `PUT /api/v1/customer/preferences`

## Users

Customer user management endpoints:

- `GET /api/v1/customer/users`
- `GET /api/v1/customer/users/{user_id}`
- `POST /api/v1/customer/users/invite`
- `PUT /api/v1/customer/users/{user_id}` — update user fields
- `POST /api/v1/customer/users/{user_id}/role` — change role in tenant
- `DELETE /api/v1/customer/users/{user_id}` — remove from tenant
- `POST /api/v1/customer/users/{user_id}/reset-password`

## Roles & Permissions

Role and permission discovery endpoints:

- `GET /api/v1/customer/permissions`
- `GET /api/v1/customer/roles`
- `POST /api/v1/customer/roles`
- `PUT /api/v1/customer/roles/{role_id}`
- `DELETE /api/v1/customer/roles/{role_id}`
- `GET /api/v1/customer/users/{user_id}/assignments`
- `PUT /api/v1/customer/users/{user_id}/assignments`
- `GET /api/v1/customer/me/permissions`

## Organization

- `GET /api/v1/customer/organization`
- `PUT /api/v1/customer/organization`

## Message Routing & Dead Letter Queue

Message routing configuration (customer plane):

- `GET /api/v1/customer/message-routes`
- `POST /api/v1/customer/message-routes`
- `PUT /api/v1/customer/message-routes/{route_id}`
- `DELETE /api/v1/customer/message-routes/{route_id}`
- `POST /api/v1/customer/message-routes/{route_id}/test`

Dead letter queue:

- `GET /api/v1/customer/dead-letter`
- `POST /api/v1/customer/dead-letter/replay-batch`
- `POST /api/v1/customer/dead-letter/{dlq_id}/replay`
- `DELETE /api/v1/customer/dead-letter/{dlq_id}`
- `DELETE /api/v1/customer/dead-letter/purge`

## Analytics

Base prefix: `/api/v1/customer/analytics`

- `GET /api/v1/customer/analytics/metrics`
- `POST /api/v1/customer/analytics/query`
- `GET /api/v1/customer/analytics/export`

## See Also

- [API Overview](overview.md)
- [WebSocket Protocol](websocket-protocol.md)
- [Service: ui-iot](../services/ui-iot.md)


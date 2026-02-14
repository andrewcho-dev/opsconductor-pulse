# OpsConductor-Pulse — API Reference

All endpoints require HTTPS. All JSON APIs require `Authorization: Bearer <jwt_token>` unless noted.

---

## Authentication

### Get a token (development)
```bash
TOKEN=$(curl -s -X POST "https://localhost/realms/pulse/protocol/openid-connect/token" \
  -d "client_id=pulse-spa" \
  -d "grant_type=password" \
  -d "username=customer1" \
  -d "password=test123" \
  --insecure | jq -r .access_token)
```

---

## Device Telemetry Ingestion (`/ingest/v1/`)

Auth: `X-Provision-Token` header (device provision token from provisioning API).

### Single message
```
POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/telemetry
```
Body:
```json
{"site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25.5, "humidity_pct": 60}}
```
Response: `202 Accepted`

### Batch (up to 100 messages)
```
POST /ingest/v1/batch
```
Body:
```json
{
  "messages": [
    {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry",
     "provision_token": "tok-xxx", "site_id": "lab-1", "seq": 1,
     "metrics": {"temp_c": 25}}
  ]
}
```
Response: `202 Accepted` with `{"accepted": N, "rejected": N, "results": [...]}`

### Error codes
| Code | Meaning |
|------|---------|
| 400 | Invalid msg_type, payload too large |
| 401 | Invalid or missing provision token |
| 403 | Device revoked or unregistered |
| 429 | Rate limited |

---

## REST API v2 (`/api/v2/`)

Auth: JWT Bearer. All responses are tenant-scoped (RLS enforced).

### Devices
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/devices` | List devices (`?limit=25&offset=0&status=&q=&site_id=`) |
| GET | `/api/v2/devices/{device_id}` | Device detail |
| GET | `/api/v2/devices/{device_id}/telemetry` | Telemetry in time range (`?from=&to=&metric=`) |
| GET | `/api/v2/devices/{device_id}/telemetry/latest` | Most recent metric values |

### Alerts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/alerts` | List alerts (`?status=OPEN&limit=50`) |
| GET | `/api/v2/alerts/{alert_id}` | Alert detail |

### Alert Rules
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/alert-rules` | List alert rules |
| GET | `/api/v2/alert-rules/{rule_id}` | Rule detail |

### WebSocket
| Path | Description |
|------|-------------|
| `WS /api/v2/ws?token=<jwt>` | Live telemetry + alert push stream |

---

## Customer APIs (`/customer/`)

Auth: JWT Bearer. All data is tenant-scoped.

### Devices
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/devices` | List devices with pagination |
| GET | `/customer/devices/{id}` | Device detail |
| PATCH | `/customer/devices/{id}` | Update name, site_id, tags |
| PATCH | `/customer/devices/{id}/decommission` | Decommission device |
| GET | `/customer/devices/{id}/tags` | Get device tags |
| PUT | `/customer/devices/{id}/tags` | Replace all tags |
| POST | `/customer/devices/{id}/tags` | Add tags |
| DELETE | `/customer/devices/{id}/tags` | Remove tags |
| GET | `/customer/devices/{id}/api-tokens` | List device API tokens |
| POST | `/customer/devices/{id}/api-tokens` | Create / rotate API token |
| DELETE | `/customer/devices/{id}/api-tokens/{token_id}` | Revoke token |
| GET | `/customer/devices/{id}/uptime` | Uptime statistics |
| POST | `/customer/devices/import` | Bulk CSV device import |

### Alerts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/alerts` | List alerts (`?status=OPEN\|ACKNOWLEDGED\|CLOSED\|ALL&limit=200&offset=0`) |
| POST | `/customer/alerts/{id}/acknowledge` | Acknowledge alert |
| POST | `/customer/alerts/{id}/close` | Close alert |
| POST | `/customer/alerts/{id}/silence` | Silence for N minutes |

### Alert Rules
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/alert-rules` | List alert rules |
| POST | `/customer/alert-rules` | Create rule |
| PATCH | `/customer/alert-rules/{id}` | Update rule |
| DELETE | `/customer/alert-rules/{id}` | Delete rule |

### Escalation Policies
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/escalation-policies` | List policies with levels |
| POST | `/customer/escalation-policies` | Create policy |
| GET | `/customer/escalation-policies/{id}` | Policy detail |
| PUT | `/customer/escalation-policies/{id}` | Update policy + levels |
| DELETE | `/customer/escalation-policies/{id}` | Delete policy |

### Notification Channels
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/notification-channels` | List channels |
| POST | `/customer/notification-channels` | Create channel (slack/pagerduty/teams/webhook) |
| GET | `/customer/notification-channels/{id}` | Channel detail |
| PUT | `/customer/notification-channels/{id}` | Update channel |
| DELETE | `/customer/notification-channels/{id}` | Delete channel |
| POST | `/customer/notification-channels/{id}/test` | Send test notification |

### Notification Routing Rules
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/notification-routing-rules` | List routing rules |
| POST | `/customer/notification-routing-rules` | Create rule |
| PUT | `/customer/notification-routing-rules/{id}` | Update rule |
| DELETE | `/customer/notification-routing-rules/{id}` | Delete rule |

### On-Call Schedules
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/oncall-schedules` | List schedules |
| POST | `/customer/oncall-schedules` | Create schedule + layers |
| GET | `/customer/oncall-schedules/{id}` | Schedule detail |
| PUT | `/customer/oncall-schedules/{id}` | Update schedule |
| DELETE | `/customer/oncall-schedules/{id}` | Delete schedule |
| GET | `/customer/oncall-schedules/{id}/current` | Who is on-call now |
| GET | `/customer/oncall-schedules/{id}/timeline?days=14` | N-day shift timeline |
| POST | `/customer/oncall-schedules/{id}/layers` | Add layer |
| PUT | `/customer/oncall-schedules/{id}/layers/{layer_id}` | Update layer |
| DELETE | `/customer/oncall-schedules/{id}/layers/{layer_id}` | Delete layer |
| GET | `/customer/oncall-schedules/{id}/overrides` | List overrides |
| POST | `/customer/oncall-schedules/{id}/overrides` | Create override |
| DELETE | `/customer/oncall-schedules/{id}/overrides/{override_id}` | Delete override |

### Reports & Exports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/reports/sla-summary?days=30` | SLA summary JSON |
| GET | `/customer/export/devices?format=csv\|json` | Export devices |
| GET | `/customer/export/alerts?format=csv\|json&days=7` | Export alerts |
| GET | `/customer/report-runs` | Report run history |

### Integrations (Legacy Delivery)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/customer/integrations` | Webhook integrations |
| GET/POST | `/customer/integrations/snmp` | SNMP integrations |
| GET/POST | `/customer/integrations/email` | Email integrations |
| GET/POST | `/customer/integrations/mqtt` | MQTT integrations |
| POST | `/customer/integrations/{type}/{id}/test` | Test delivery |
| GET/POST | `/customer/integration-routes` | Alert routing rules |
| GET | `/customer/delivery-status` | Recent delivery attempts |

### Sites
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/sites` | List sites |
| POST | `/customer/sites` | Create site |
| PUT | `/customer/sites/{id}` | Update site |
| DELETE | `/customer/sites/{id}` | Delete site |

### Subscriptions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/subscriptions` | List subscriptions |
| GET | `/customer/subscriptions/{id}` | Subscription detail |
| GET | `/customer/subscription/audit` | Subscription audit history |
| POST | `/customer/subscription/renew` | Request renewal |

### Users
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/users` | List tenant users (tenant-admin only) |
| POST | `/customer/users` | Invite user |
| DELETE | `/customer/users/{id}` | Remove user |

### Metrics Catalog
| Method | Path | Description |
|--------|------|-------------|
| GET/POST/DELETE | `/customer/metrics/catalog` | Metric catalog CRUD |
| GET/POST/PATCH/DELETE | `/customer/normalized-metrics` | Normalized metric definitions |
| GET/POST/PATCH/DELETE | `/customer/metric-mappings` | Raw → normalized mappings |

### Misc
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/tags` | All tenant tags |
| GET | `/customer/geocode` | Geocode address |
| GET | `/customer/fleet/uptime-summary` | Fleet-wide uptime summary |

---

## Operator APIs (`/operator/`)

Auth: JWT Bearer with `operator` or `operator-admin` role. All access is audited. BYPASSRLS.

### Fleet Views
| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/devices` | All devices (`?tenant_id=&status=&limit=`) |
| GET | `/operator/alerts` | All alerts (`?tenant_id=&status=`) |
| GET | `/operator/quarantine` | Quarantine events |
| GET | `/operator/integrations` | All integrations |

### System Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/system/health` | Service health (Postgres, MQTT, Keycloak, services) |
| GET | `/operator/system/metrics` | Throughput, queue depth, last activity |
| GET | `/operator/system/metrics/history` | Historical metrics (`?rate=true` for throughput rates) |
| GET | `/operator/system/capacity` | Disk, DB connections, table sizes |
| GET | `/operator/system/aggregates` | Platform totals (tenants, devices, alerts) |
| GET | `/operator/system/errors` | Recent errors and failures |

### Tenants (operator-admin)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/tenants` | List all tenants |
| POST | `/operator/tenants` | Create tenant |
| GET | `/operator/tenants/{id}` | Tenant detail |
| PATCH | `/operator/tenants/{id}` | Update tenant |
| DELETE | `/operator/tenants/{id}` | Delete tenant |
| GET | `/operator/tenants/stats/summary` | Platform stats |
| GET | `/operator/tenants/{id}/stats` | Per-tenant stats |
| GET | `/operator/tenants/{id}/devices` | Tenant device list |

### Subscriptions (operator)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/subscriptions` | All subscriptions |
| POST | `/operator/subscriptions` | Create subscription |
| GET | `/operator/subscriptions/{id}` | Subscription detail |
| PATCH | `/operator/subscriptions/{id}` | Update subscription |
| POST | `/operator/devices/{id}/subscription` | Assign device to subscription |
| GET | `/operator/subscriptions/expiring` | Expiring subscriptions |
| GET | `/operator/subscriptions/summary` | Platform summary |

### Admin (operator-admin)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/audit-log` | Operator audit log |
| POST | `/operator/settings` | Update system settings |

---

## Provisioning API (`/api/admin/`)

Auth: `X-Admin-Key` header. Served on port 8081 (not behind Caddy).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admin/devices` | Provision a new device |
| POST | `/api/admin/devices/{id}/activate-code` | Generate activation code |

### Provision a device
```bash
curl -X POST http://localhost:8081/api/admin/devices \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "tenant-a", "device_id": "sensor-001", "site_id": "lab-1"}'
```

---

## Common Query Parameters

### Alert status values
`OPEN` | `ACKNOWLEDGED` | `CLOSED` | `ALL`

> **Important**: Severity filtering (CRITICAL/HIGH/MEDIUM/LOW) is done client-side.
> The API does not accept severity as a `status` parameter — only the 4 values above are valid.

### Severity mapping
| Level | Severity value |
|-------|---------------|
| LOW | 1–2 |
| MEDIUM | 3 |
| HIGH | 4 |
| CRITICAL | 5+ |

### Pagination
Most list endpoints accept `?limit=N&offset=N`. Max `limit` on `/customer/alerts` is **200**.

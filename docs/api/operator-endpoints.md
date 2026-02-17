---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/operator.py
  - services/ui_iot/routes/system.py
  - services/ui_iot/routes/users.py
  - services/ui_iot/routes/roles.py
  - services/ui_iot/routes/analytics.py
  - services/ui_iot/routes/organization.py
  - services/ui_iot/routes/message_routing.py
phases: [30, 43, 65, 97, 130, 142]
---

# Operator API Endpoints

> Cross-tenant admin API for operators. All access is audited.

## Auth

Operator endpoints require:

- JWT bearer auth
- Operator role (`operator` or `operator-admin`)

In examples:

```bash
BASE="https://localhost"
H_AUTH=(-H "Authorization: Bearer $TOKEN" --insecure)
```

## Tenant Management

Base prefix: `/api/v1/operator`

From `services/ui_iot/routes/operator.py`:

- `GET /api/v1/operator/tenants`
- `POST /api/v1/operator/tenants`
- `GET /api/v1/operator/tenants/{tenant_id}`
- `PATCH /api/v1/operator/tenants/{tenant_id}`
- `DELETE /api/v1/operator/tenants/{tenant_id}`
- `GET /api/v1/operator/tenants/{tenant_id}/stats`
- `GET /api/v1/operator/tenants/stats/summary`

Example:

```bash
curl -s "${H_AUTH[@]}" "$BASE/api/v1/operator/tenants?limit=100&offset=0"
```

## Cross-Tenant Device & Alert Inventory

- `GET /api/v1/operator/devices`
- `GET /api/v1/operator/tenants/{tenant_id}/devices`
- `GET /api/v1/operator/tenants/{tenant_id}/devices/{device_id}`
- `GET /api/v1/operator/alerts`
- `GET /api/v1/operator/quarantine`

## System Health & Metrics

Base prefix: `/api/v1/operator/system`

- `GET /api/v1/operator/system/health`
- `GET /api/v1/operator/system/metrics`
- `GET /api/v1/operator/system/metrics/history`
- `GET /api/v1/operator/system/metrics/history/batch`
- `GET /api/v1/operator/system/metrics/latest`
- `GET /api/v1/operator/system/capacity`
- `GET /api/v1/operator/system/aggregates`
- `GET /api/v1/operator/system/errors`

Example:

```bash
curl -s "${H_AUTH[@]}" "$BASE/api/v1/operator/system/health"
```

## User Management (Keycloak Admin)

Operator user admin endpoints (from `services/ui_iot/routes/users.py`):

- `GET /api/v1/operator/users`
- `GET /api/v1/operator/users/{user_id}`
- `POST /api/v1/operator/users`
- `PUT /api/v1/operator/users/{user_id}`
- `DELETE /api/v1/operator/users/{user_id}`
- `POST /api/v1/operator/users/{user_id}/enable`
- `POST /api/v1/operator/users/{user_id}/disable`
- `POST /api/v1/operator/users/{user_id}/roles`
- `DELETE /api/v1/operator/users/{user_id}/roles/{role_name}`
- `POST /api/v1/operator/users/{user_id}/tenant`
- `POST /api/v1/operator/users/{user_id}/reset-password`
- `POST /api/v1/operator/users/{user_id}/send-welcome-email`
- `POST /api/v1/operator/users/{user_id}/password`
- `GET /api/v1/operator/organizations`

## Subscriptions, Plans, and Tier Allocations

- `POST /api/v1/operator/subscriptions`
- `GET /api/v1/operator/subscriptions`
- `GET /api/v1/operator/subscriptions/{subscription_id}`
- `PATCH /api/v1/operator/subscriptions/{subscription_id}`
- `GET /api/v1/operator/subscriptions/summary`
- `GET /api/v1/operator/subscriptions/expiring`
- `GET /api/v1/operator/subscriptions/expiring-notifications`

Tier allocation management:

- `GET /api/v1/operator/subscriptions/{subscription_id}/tier-allocations`
- `POST /api/v1/operator/subscriptions/{subscription_id}/tier-allocations`
- `PUT /api/v1/operator/subscriptions/{subscription_id}/tier-allocations/{tier_id}`
- `DELETE /api/v1/operator/subscriptions/{subscription_id}/tier-allocations/{tier_id}`
- `POST /api/v1/operator/subscriptions/{subscription_id}/sync-tier-allocations`
- `POST /api/v1/operator/subscriptions/{subscription_id}/reconcile-tiers`

Plans:

- `GET /api/v1/operator/plans`
- `POST /api/v1/operator/plans`
- `PUT /api/v1/operator/plans/{plan_id}`
- `GET /api/v1/operator/plans/{plan_id}/tier-defaults`
- `PUT /api/v1/operator/plans/{plan_id}/tier-defaults`

Operator tier assignment bypass:

- `PUT /api/v1/operator/devices/tier`

## Device Tiers (Operator)

- `GET /api/v1/operator/device-tiers`
- `POST /api/v1/operator/device-tiers`
- `PUT /api/v1/operator/device-tiers/{tier_id}`

## Operator Audit Log

- `GET /api/v1/operator/audit-log`

## Certificates (Operator)

Base prefix: `/api/v1/operator`

- `GET /api/v1/operator/certificates`
- `GET /api/v1/operator/ca-bundle`

## Settings

- `POST /api/v1/operator/settings`

## Notes on Sources

Some files listed in `sources` above contain customer-plane endpoints (`roles.py`, `analytics.py`, `organization.py`, `message_routing.py`). This doc only enumerates endpoints that are actually routed under `/api/v1/operator/*` in the current codebase.

## See Also

- [API Overview](overview.md)
- [Customer Endpoints](customer-endpoints.md)
- [Service Map](../architecture/service-map.md)
- [Security](../operations/security.md)


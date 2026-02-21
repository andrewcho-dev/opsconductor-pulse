# Phase 60: Operator Tenant Onboarding UI

## What Exists

Backend operator API is already comprehensive (25+ endpoints in operator.py):
- `GET /operator/tenants` — list all tenants
- `GET /operator/tenants/{tenant_id}` — tenant details
- `GET /operator/tenants/{tenant_id}/stats` — stats
- `POST /operator/tenants` — create tenant (admin only)
- `PATCH /operator/tenants/{tenant_id}` — update tenant
- `DELETE /operator/tenants/{tenant_id}` — soft delete
- `GET /operator/subscriptions` — list subscriptions
- `POST /operator/subscriptions` — create subscription
- `PATCH /operator/subscriptions/{id}` — update subscription
- `GET /operator/audit-log` — audit log with filters

Operator frontend exists but is read-only (operator dashboard shows stats).

## What This Phase Adds (Frontend Only — No Backend Changes)

1. **Tenant list page** (`/operator/tenants`) — table of tenants with status, device count, alert count
2. **Tenant detail page** (`/operator/tenants/:tenantId`) — stats, subscription info, device list, recent alerts
3. **Create Tenant modal** — form → POST /operator/tenants
4. **Subscription management panel** — view/create/update subscriptions per tenant
5. **Audit log page** (`/operator/audit-log`) — filterable table of audit events
6. **Operator nav updates** — Tenants, Audit Log links

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | API client: operator tenant + subscription + audit functions |
| 002 | Frontend: Tenant list + create modal |
| 003 | Frontend: Tenant detail + subscription panel |
| 004 | Frontend: Audit log page |
| 005 | Frontend: Nav wiring + routes |
| 006 | Unit tests |
| 007 | Verify |

## Key Files

- `frontend/src/services/api/operator.ts` — new or extend (prompt 001)
- `frontend/src/features/operator/` — existing operator pages (prompts 002–005)
- Operator router — prompt 005

# Phase 21: CRUD Pages + Operator Views

## Overview

Phases 18-20 built the React SPA foundation (shell, auth, dashboard, device detail charts). Nine page stubs remain in the router that just render placeholder text. Phase 21 implements all of them:

**Customer pages** (5 pages):
1. Alert Rules — CRUD with create/edit dialog
2. Webhooks — CRUD with test delivery
3. SNMP — CRUD with test delivery
4. Email — CRUD with test delivery
5. MQTT — CRUD with test delivery

**Operator pages** (4 pages):
6. Operator Dashboard — cross-tenant stats overview
7. Operator Devices — cross-tenant device table with filtering
8. Audit Log — operator activity log with filtering
9. Settings — system mode and reject settings

---

## Backend API Reference

### Customer Endpoints (Bearer auth via Keycloak token)

**Alert Rules**:
| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v2/alert-rules` | List rules (JSON) |
| GET | `/customer/alert-rules/{id}` | Get single rule |
| POST | `/customer/alert-rules` | Create (requires customer_admin) |
| PATCH | `/customer/alert-rules/{id}` | Update (requires customer_admin) |
| DELETE | `/customer/alert-rules/{id}` | Delete (requires customer_admin) |

**Webhook Integrations**:
| Method | Path | Notes |
|--------|------|-------|
| GET | `/customer/integrations` | List webhooks (`{integrations: [...]}`) |
| GET | `/customer/integrations/{id}` | Get single |
| POST | `/customer/integrations` | Create |
| PATCH | `/customer/integrations/{id}` | Update |
| DELETE | `/customer/integrations/{id}` | Delete |
| POST | `/customer/integrations/{id}/test` | Test delivery |

**SNMP Integrations**:
| Method | Path | Notes |
|--------|------|-------|
| GET | `/customer/integrations/snmp` | List (returns array directly) |
| GET | `/customer/integrations/snmp/{id}` | Get single |
| POST | `/customer/integrations/snmp` | Create |
| PATCH | `/customer/integrations/snmp/{id}` | Update |
| DELETE | `/customer/integrations/snmp/{id}` | Delete |
| POST | `/customer/integrations/snmp/{id}/test` | Test |

**Email Integrations**:
| Method | Path | Notes |
|--------|------|-------|
| GET | `/customer/integrations/email` | List (returns array directly) |
| POST | `/customer/integrations/email` | Create |
| PATCH | `/customer/integrations/email/{id}` | Update |
| DELETE | `/customer/integrations/email/{id}` | Delete |
| POST | `/customer/integrations/email/{id}/test` | Test |

**MQTT Integrations**:
| Method | Path | Notes |
|--------|------|-------|
| GET | `/customer/integrations/mqtt` | List (returns array directly) |
| POST | `/customer/integrations/mqtt` | Create |
| PATCH | `/customer/integrations/mqtt/{id}` | Update |
| DELETE | `/customer/integrations/mqtt/{id}` | Delete |
| POST | `/customer/integrations/mqtt/{id}/test` | Test |

### Operator Endpoints (Bearer auth, requires operator role)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/operator/devices?tenant_filter=&limit=&offset=` | `{devices, tenant_filter, limit, offset}` |
| GET | `/operator/alerts?tenant_filter=&status=&limit=` | `{alerts, tenant_filter, status, limit}` |
| GET | `/operator/quarantine?minutes=&limit=` | `{minutes, events, limit}` |
| GET | `/operator/integrations?tenant_filter=` | `{integrations, tenant_filter}` |
| GET | `/operator/audit-log?user_id=&action=&since=&limit=` | `{entries, limit, ...}` (operator_admin only) |
| GET | `/operator/settings?format=json` | Settings JSON (operator_admin, needs backend tweak) |
| POST | `/operator/settings` | Update mode/rejects (operator_admin, form data) |

---

## Auth Context

```typescript
const { user, isCustomer, isOperator } = useAuth();
// user.role: "customer_admin" | "customer_viewer" | "operator" | "operator_admin"
// isCustomer: customer_admin || customer_viewer
// isOperator: operator || operator_admin
```

Customer CRUD operations (create, update, delete) require `customer_admin` role.
Operator settings require `operator_admin` role.

---

## Task Execution Order

| # | File | Description | Dependencies |
|---|------|-------------|-------------|
| 1 | `001-api-client-layer.md` | Types, API functions, hooks for all CRUD endpoints | None |
| 2 | `002-alert-rules-page.md` | Alert rules list + create/edit dialog | #1 |
| 3 | `003-integration-pages.md` | Webhook, SNMP, Email, MQTT pages | #1 |
| 4 | `004-operator-pages.md` | Operator dashboard, devices, audit log, settings | #1 |
| 5 | `005-tests-and-documentation.md` | Build verification, backend tests, documentation | #1-#4 |

Execute tasks in order. Each task has its own test section.

---

## Key Constraints

1. **No backend changes** in Tasks 1-3. Customer endpoints already support Bearer auth and return JSON.
2. **Minimal backend change** in Task 4: add `?format=json` to operator settings GET endpoint.
3. **Dynamic metrics**: Alert rule metric names are freeform strings (e.g., `temp_c`, `battery_pct`, `pressure_psi`).
4. **SSRF protection**: Backend validates webhook URLs and SNMP hosts. The SPA doesn't need to duplicate this validation — just show backend error messages to users.
5. **Role-based UI**: Hide create/edit/delete buttons for `customer_viewer` users. Show operator pages only for operator role.
6. **Dark theme**: All forms and dialogs must match the existing dark theme.
7. **Existing patterns**: Follow the established patterns from Phase 19/20 — shadcn components, TanStack Query hooks, WidgetErrorBoundary, React.memo where appropriate.

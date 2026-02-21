# Phase 133 -- Hotfix: Operator Certificate Endpoints

## Problem

Operator UI is calling customer certificate endpoints:

- `GET /api/v1/customer/certificates`
- `GET /api/v1/customer/ca-bundle`

In some deployments (notably with PgBouncer transaction pooling), operator tokens may not include an `organization` / `tenant_id` claim. The customer endpoints rely on tenant context via `get_tenant_id()`, so these requests return `401` even though the user is authenticated.

## Fix

Add true operator endpoints that:

- do not require tenant context
- use `SET LOCAL ROLE pulse_operator` to bypass RLS for fleet-wide listing

Update the frontend operator certificates page to call the operator endpoints.

## Execution Order

| # | File | Commit message |
|---|------|----------------|
| 1 | `001-operator-certificate-endpoints.md` | `fix: add operator certificate endpoints and frontend wiring` |


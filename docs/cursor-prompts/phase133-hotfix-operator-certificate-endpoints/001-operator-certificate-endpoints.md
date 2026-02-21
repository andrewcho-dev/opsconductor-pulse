# 001 -- Add Operator Certificate Endpoints

## Goal

Stop `401` errors on the operator certificates page by adding operator-scoped certificate endpoints that do not depend on tenant context, and wire the frontend to use them.

## Context

Customer endpoints are under `/api/v1/customer/...` and depend on `get_tenant_id()` for scoping. In environments where JSON/JWT claims do not include an `organization` (tenant) claim for operator users, tenant context is unset and customer routes return `401` even though authentication succeeded.

## Task

### Step 1: Backend -- add operator router + endpoints

File: `services/ui_iot/routes/certificates.py`

1. Add an operator router:

- `operator_router = APIRouter(prefix="/api/v1/operator", dependencies=[JWTBearer, inject_tenant_context, require_operator])`

2. Add operator endpoints:

- `GET /api/v1/operator/certificates`
  - Optional query params:
    - `tenant_id` (string)
    - `status` (ACTIVE/REVOKED/EXPIRED)
    - `limit` (default 100)
    - `offset` (default 0)
  - Uses `SET LOCAL ROLE pulse_operator` and queries `device_certificates` directly (bypass RLS).
  - Returns the same shape as the customer list endpoint:
    - `{ certificates: [...], total, limit, offset }`

- `GET /api/v1/operator/ca-bundle`
  - Returns the Device CA PEM bundle (raw text), no tenant context required.

3. Ensure `require_operator` is imported (it is not available from `routes.customer` wildcard import).

### Step 2: Backend -- register the operator router

File: `services/ui_iot/app.py`

- Import the operator router from `routes.certificates` and include it:
  - `app.include_router(operator_certificates_router)`

### Step 3: Frontend -- use operator endpoints

Files:

- `frontend/src/services/api/certificates.ts`
  - Change `listAllCertificates()` to call:
    - `GET /api/v1/operator/certificates`
  - Add `downloadOperatorCaBundle()` to fetch:
    - `GET /api/v1/operator/ca-bundle`

- `frontend/src/features/operator/CertificateOverviewPage.tsx`
  - Use `downloadOperatorCaBundle()` instead of the customer CA bundle fetch.

## Verification

```bash
# Backend rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# Operator endpoints should exist (401 without token is OK)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/v1/operator/certificates
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/v1/operator/ca-bundle

# Frontend build
cd frontend && npm run build
```

Manual:

- Login as operator (no tenant claim required)
- Navigate to `/app/operator/certificates`
- Confirm the page loads without repeated `401` calls to `/api/v1/customer/certificates`

## Commit

```
fix: add operator certificate endpoints and frontend wiring
```


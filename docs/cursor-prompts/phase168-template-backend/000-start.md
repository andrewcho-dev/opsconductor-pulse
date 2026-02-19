# Phase 168 — Template Management Backend

## Goal

Create REST API endpoints for template CRUD (customer + operator) so templates can be created, read, updated, deleted, and cloned via the API.

## Prerequisites

- Phase 166-167 complete (all template + instance tables exist)
- Existing route patterns in `services/ui_iot/routes/` (see `carrier.py`, `sensors.py`)
- Router registration pattern in `services/ui_iot/app.py`

## Key Patterns to Reuse

- **Router setup**: `APIRouter(prefix="/api/v1/customer", dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context), Depends(require_customer)])`
- **DB access**: `pool=Depends(get_db_pool)` + `tenant_connection(pool, tenant_id)` for customer routes
- **Operator**: `operator_connection(pool)` + `log_operator_access()` for operator routes
- **Pydantic models**: Create/Update models with `Field()` validators (see `CarrierIntegrationCreate`)
- **Error handling**: `try/except HTTPException: raise; except Exception: logger.exception(); raise HTTPException(500)`

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-template-crud.md` | Customer template CRUD + sub-resource endpoints |
| 2 | `002-operator-templates.md` | Operator template management endpoints |
| 3 | `003-update-docs.md` | Update API and service docs |

## Verification

```bash
cd services/ui_iot && python -c "
from app import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/api/v1/customer/templates' in routes
assert '/api/v1/customer/templates/{template_id}' in routes
assert '/api/v1/operator/templates' in routes
print('All template routes registered')
"
```

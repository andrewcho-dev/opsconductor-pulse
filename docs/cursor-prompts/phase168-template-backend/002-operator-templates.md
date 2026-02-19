# Task 2: Operator Template Endpoints

## Modify file: `services/ui_iot/routes/operator.py`

Add operator template management endpoints to the existing operator router. Follow the existing patterns in `operator.py` (see the tenant management endpoints for reference).

### Key patterns from operator.py

- Router prefix: `/api/v1/operator`
- Dependencies: `JWTBearer()`, `inject_tenant_context`, `require_operator`
- DB access: `operator_connection(pool)` which sets `ROLE pulse_operator` (bypasses RLS)
- Audit logging: `log_operator_access(conn, user_id, action, ...)` after every operation
- Request metadata: `ip, user_agent = get_request_metadata(request)`

### New Endpoints

**GET /operator/templates** — List all templates cross-tenant
```python
@router.get("/templates")
async def operator_list_templates(
    request: Request,
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
```
- Use `operator_connection(pool)` to bypass RLS
- Query all templates with optional filters (category, source, tenant_id, search)
- Include a count query for pagination
- Log access: `log_operator_access(conn, user_id, "list_templates", ...)`
- Return `{"items": [...], "total": N}`

**POST /operator/templates** — Create system template
```python
@router.post("/templates", status_code=201)
async def operator_create_template(
    request: Request,
    body: TemplateCreate,  # Import from routes.templates
    pool=Depends(get_db_pool),
):
```
- Use `operator_connection(pool)`
- Insert with `tenant_id = NULL`, `is_locked = true`, `source = 'system'`
- Log access: `log_operator_access(conn, user_id, "create_system_template", ...)`
- Return created template

**PUT /operator/templates/{template_id}** — Update any template
```python
@router.put("/templates/{template_id}")
async def operator_update_template(
    request: Request,
    template_id: int,
    body: TemplateUpdate,  # Import from routes.templates
    pool=Depends(get_db_pool),
):
```
- Use `operator_connection(pool)` — operators can edit even locked templates
- Dynamic UPDATE from `model_dump(exclude_unset=True)`
- Log access
- Return updated template

**DELETE /operator/templates/{template_id}** — Delete any template
```python
@router.delete("/templates/{template_id}", status_code=204)
async def operator_delete_template(
    request: Request,
    template_id: int,
    pool=Depends(get_db_pool),
):
```
- Check if devices reference it: 409 if in use
- Delete (cascades)
- Log access
- Return `Response(status_code=204)`

### Import the Pydantic models

At the top of `operator.py`, add:
```python
from routes.templates import TemplateCreate, TemplateUpdate
```

Or, if circular import is a concern, define the models in a shared location or duplicate them.

### Audit logging actions

Use these action strings for `log_operator_access`:
- `"list_templates"` — listing templates
- `"create_system_template"` — creating a system template
- `"update_template"` — updating any template
- `"delete_template"` — deleting a template

### Operator sub-resource management

Operators should also be able to manage metrics, commands, and slots on any template (including locked ones). Add operator endpoints for these:

- `POST /operator/templates/{template_id}/metrics` — Create metric on any template
- `PUT /operator/templates/{template_id}/metrics/{metric_id}` — Update metric
- `DELETE /operator/templates/{template_id}/metrics/{metric_id}` — Delete metric

Same pattern for commands and slots. The key difference from customer routes: no `is_locked` check, use `operator_connection()`, and audit log every operation.

## Verification

```python
from app import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
op_template_routes = [r for r in routes if 'operator' in r and 'template' in r]
assert len(op_template_routes) >= 4
print(f"Operator template routes: {op_template_routes}")
```

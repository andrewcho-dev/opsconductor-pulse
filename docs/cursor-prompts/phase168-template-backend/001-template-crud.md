# Task 1: Customer Template CRUD + Sub-Resources

## Create file: `services/ui_iot/routes/templates.py`

Create a new route file for template management. Follow the exact patterns from `carrier.py` and `sensors.py`.

### Imports

```python
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer
from db.pool import tenant_connection
from dependencies import get_db_pool

logger = logging.getLogger(__name__)
```

### Router Setup

```python
router = APIRouter(
    prefix="/api/v1/customer",
    tags=["templates"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)
```

### Pydantic Models

**TemplateCreate:**
```python
class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str | None = None
    category: str = Field(..., pattern=r"^(gateway|edge_device|standalone_sensor|controller|expansion_module)$")
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    firmware_version_pattern: str | None = None
    transport_defaults: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    image_url: str | None = None
```

**TemplateUpdate:** (all fields optional)
```python
class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, pattern=r"^(gateway|edge_device|standalone_sensor|controller|expansion_module)$")
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    firmware_version_pattern: str | None = None
    transport_defaults: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    image_url: str | None = None
```

**TemplateMetricCreate/Update, TemplateCommandCreate/Update, TemplateSlotCreate/Update:**
Define similar Create/Update model pairs for each sub-resource, mapping to the respective table columns from migration 109. Include:
- Metric: `metric_key` (pattern: `^[a-zA-Z][a-zA-Z0-9_]*$`), `display_name`, `data_type`, `unit`, `min_value`, `max_value`, `precision_digits`, `is_required`, `description`, `enum_values`, `sort_order`
- Command: `command_key` (same pattern), `display_name`, `description`, `parameters_schema`, `response_schema`, `sort_order`
- Slot: `slot_key`, `display_name`, `slot_type`, `interface_type`, `max_devices`, `compatible_templates` (list[int] | None), `is_required`, `description`, `sort_order`

### Template Endpoints

**GET /templates** — List templates visible to tenant (system + own)
```python
@router.get("/templates")
async def list_templates(
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
    search: str | None = Query(default=None),
    pool=Depends(get_db_pool),
):
```
- Query: `SELECT * FROM device_templates WHERE (tenant_id IS NULL OR tenant_id = $1)` + optional filters
- Sort by `source DESC` (system first), then `name`
- Return list of template dicts (without sub-resources for performance)

**GET /templates/{template_id}** — Full template with metrics, commands, slots
```python
@router.get("/templates/{template_id}")
async def get_template(template_id: int, pool=Depends(get_db_pool)):
```
- Fetch template row, 404 if not found
- RLS ensures tenant can only see own + system templates
- Also fetch `template_metrics`, `template_commands`, `template_slots` for this template_id
- Return combined dict: `{...template, "metrics": [...], "commands": [...], "slots": [...]}`

**POST /templates** — Create tenant template
```python
@router.post("/templates", status_code=201)
async def create_template(body: TemplateCreate, pool=Depends(get_db_pool)):
```
- Insert with `tenant_id = get_tenant_id()`, `is_locked = false`, `source = 'tenant'`
- Return created template

**PUT /templates/{template_id}** — Update own template
```python
@router.put("/templates/{template_id}")
async def update_template(template_id: int, body: TemplateUpdate, pool=Depends(get_db_pool)):
```
- Fetch template first; 404 if not found, 403 if `is_locked = true`
- Use `model_dump(exclude_unset=True)` to build dynamic UPDATE
- Return updated template

**DELETE /templates/{template_id}** — Delete own template
```python
@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: int, pool=Depends(get_db_pool)):
```
- Fetch template first; 404 if not found, 403 if `is_locked = true`
- Check if any devices reference this template: `SELECT count(*) FROM device_registry WHERE template_id = $1`; 409 if in use
- Delete (cascades to metrics, commands, slots)
- Return `Response(status_code=204)`

**POST /templates/{template_id}/clone** — Clone system template into tenant-owned copy
```python
@router.post("/templates/{template_id}/clone", status_code=201)
async def clone_template(template_id: int, pool=Depends(get_db_pool)):
```
- Fetch source template; 404 if not found
- Insert new template with `tenant_id = get_tenant_id()`, `is_locked = false`, `source = 'tenant'`, `slug = "{original_slug}-copy"` or `"{original_slug}-{tenant_shortid}"`
- Copy all metrics, commands, slots from source to new template (adjust template_id)
- Return new template with sub-resources

### Sub-Resource Endpoints (Metrics, Commands, Slots)

For each sub-resource type, implement 3 endpoints that:
1. Verify the parent template exists and is editable (not locked, belongs to tenant)
2. Perform the CRUD operation

**Pattern for all three:**

```python
@router.post("/templates/{template_id}/metrics", status_code=201)
async def create_template_metric(template_id: int, body: TemplateMetricCreate, pool=Depends(get_db_pool)):
    # Verify template is editable
    # INSERT into template_metrics
    # Return created metric

@router.put("/templates/{template_id}/metrics/{metric_id}")
async def update_template_metric(template_id: int, metric_id: int, body: TemplateMetricUpdate, pool=Depends(get_db_pool)):
    # Verify template is editable
    # UPDATE template_metrics WHERE id = metric_id AND template_id = template_id
    # Return updated metric

@router.delete("/templates/{template_id}/metrics/{metric_id}", status_code=204)
async def delete_template_metric(template_id: int, metric_id: int, pool=Depends(get_db_pool)):
    # Verify template is editable
    # DELETE from template_metrics WHERE id = metric_id AND template_id = template_id
    # Return Response(status_code=204)
```

Repeat this pattern for `/commands/{command_id}` and `/slots/{slot_id}`.

### Helper function for template editability check

Create a reusable helper:

```python
async def _get_editable_template(conn, template_id: int, tenant_id: str):
    """Fetch template and verify it's editable by the current tenant."""
    row = await conn.fetchrow(
        "SELECT * FROM device_templates WHERE id = $1",
        template_id,
    )
    if not row:
        raise HTTPException(404, "Template not found")
    if row["is_locked"]:
        raise HTTPException(403, "Cannot modify a locked system template")
    if row["tenant_id"] != tenant_id:
        raise HTTPException(403, "Cannot modify another tenant's template")
    return row
```

### Register Router in `app.py`

Add to imports section:
```python
from routes.templates import router as templates_router
```

Add to router registration section (near the other routers):
```python
app.include_router(templates_router)
```

## Verification

```python
# Quick smoke test
from app import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
template_routes = [r for r in routes if 'template' in r]
assert len(template_routes) >= 10  # list, get, create, update, delete, clone + sub-resources
print(f"Template routes: {template_routes}")
```

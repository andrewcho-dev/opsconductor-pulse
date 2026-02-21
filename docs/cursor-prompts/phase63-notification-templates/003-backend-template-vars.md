# Prompt 003 — Backend: GET /customer/integrations/{id}/template-variables

Read `services/ui_iot/routes/customer.py`.

## Add Endpoint

```python
TEMPLATE_VARIABLES = [
    {"name": "alert_id",      "type": "integer", "description": "Numeric alert ID"},
    {"name": "device_id",     "type": "string",  "description": "Device identifier"},
    {"name": "site_id",       "type": "string",  "description": "Site identifier"},
    {"name": "tenant_id",     "type": "string",  "description": "Tenant identifier"},
    {"name": "severity",      "type": "integer", "description": "Severity level (0=critical, 3=info)"},
    {"name": "severity_label","type": "string",  "description": "Severity label: CRITICAL, WARNING, INFO"},
    {"name": "alert_type",    "type": "string",  "description": "Alert type: THRESHOLD, NO_HEARTBEAT, etc."},
    {"name": "summary",       "type": "string",  "description": "Alert summary text"},
    {"name": "status",        "type": "string",  "description": "Alert status: OPEN, ACKNOWLEDGED, CLOSED"},
    {"name": "created_at",    "type": "string",  "description": "ISO 8601 creation timestamp"},
    {"name": "details",       "type": "object",  "description": "Alert details (JSONB dict)"},
]

@router.get("/integrations/{integration_id}/template-variables",
            dependencies=[Depends(require_customer)])
async def get_template_variables(integration_id: str, pool=Depends(get_db_pool)):
    """Returns the list of Jinja2 template variables available for notification templates."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            "SELECT integration_id, type FROM integrations WHERE tenant_id=$1 AND integration_id=$2",
            tenant_id, integration_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {
        "integration_id": integration_id,
        "type": row["type"],
        "variables": TEMPLATE_VARIABLES,
        "syntax": "Jinja2 — use {{ variable_name }} syntax",
        "example": "Alert {{ alert_id }}: {{ severity_label }} — {{ summary }}",
    }
```

## Acceptance Criteria

- [ ] GET /customer/integrations/{id}/template-variables returns 11 variables
- [ ] 404 if integration not found for tenant
- [ ] Returns `syntax` and `example` fields
- [ ] `pytest -m unit -v` passes

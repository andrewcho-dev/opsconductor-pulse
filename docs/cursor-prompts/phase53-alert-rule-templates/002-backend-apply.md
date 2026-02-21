# Prompt 002 — Backend: POST /customer/alert-rule-templates/apply

Read `services/ui_iot/routes/customer.py` — find the existing `create_alert_rule` endpoint to understand the insert pattern.

## Add Bulk-Apply Endpoint

This endpoint creates alert rules from one or more templates for the current tenant, skipping any that already exist by name.

```python
class ApplyTemplatesRequest(BaseModel):
    template_ids: list[str] = Field(..., min_items=1)
    site_ids: Optional[list[str]] = None  # optional: apply to specific sites

@router.post("/alert-rule-templates/apply", dependencies=[Depends(require_customer)])
async def apply_alert_rule_templates(body: ApplyTemplatesRequest, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    template_map = {t["template_id"]: t for t in ALERT_RULE_TEMPLATES}

    requested = [template_map[tid] for tid in body.template_ids if tid in template_map]
    if not requested:
        raise HTTPException(status_code=400, detail="No valid template_ids provided")

    created = []
    skipped = []

    async with tenant_connection(pool, tenant_id) as conn:
        for tmpl in requested:
            # Skip if a rule with this name already exists for tenant
            existing = await conn.fetchval(
                "SELECT id FROM alert_rules WHERE tenant_id = $1 AND name = $2",
                tenant_id, tmpl["name"]
            )
            if existing:
                skipped.append(tmpl["template_id"])
                continue
            row = await conn.fetchrow(
                """
                INSERT INTO alert_rules
                    (tenant_id, name, description, metric_name, operator, threshold,
                     severity, duration_seconds, device_type, site_ids, enabled)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,true)
                RETURNING id, name
                """,
                tenant_id, tmpl["name"], tmpl["description"], tmpl["metric_name"],
                tmpl["operator"], tmpl["threshold"], tmpl["severity"],
                tmpl["duration_seconds"], tmpl["device_type"],
                body.site_ids or None
            )
            created.append({"id": row["id"], "name": row["name"],
                            "template_id": tmpl["template_id"]})

    return {"created": created, "skipped": skipped}
```

## Acceptance Criteria

- [ ] POST /customer/alert-rule-templates/apply creates rules from given template_ids
- [ ] Skips rules whose name already exists for the tenant
- [ ] Returns `created` list and `skipped` list
- [ ] Optional `site_ids` applied to all created rules
- [ ] Invalid template_ids silently ignored (not in map)
- [ ] Empty result after all skipped returns 200 with empty created list
- [ ] `pytest -m unit -v` passes

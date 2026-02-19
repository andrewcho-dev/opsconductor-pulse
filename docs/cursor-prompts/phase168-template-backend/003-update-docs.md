# Task 3: Update Documentation

## Files to Update

### 1. `docs/api/customer-endpoints.md`

Add a new "Device Templates" section documenting:
- `GET /api/v1/customer/templates` — List templates (query params: category, source, search)
- `GET /api/v1/customer/templates/{template_id}` — Get full template with sub-resources
- `POST /api/v1/customer/templates` — Create tenant template
- `PUT /api/v1/customer/templates/{template_id}` — Update own template (403 if locked)
- `DELETE /api/v1/customer/templates/{template_id}` — Delete own template (409 if devices using it)
- `POST /api/v1/customer/templates/{template_id}/clone` — Clone system template
- Sub-resource CRUD for metrics, commands, slots

### 2. `docs/services/ui-iot.md`

Add `routes/templates.py` to the route file listing. Note the new router registration in `app.py`.

### 3. `docs/architecture/overview.md`

Update the Template Model section to mention the API layer and access control rules:
- Tenants can only modify their own templates (not locked ones)
- Operators can modify any template including system locked ones
- Clone operation creates tenant-owned copy of system templates

### For Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 168 changes
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-19`
   - Add `168` to the `phases` array
   - Add `services/ui_iot/routes/templates.py` to `sources`
4. Verify no stale information remains

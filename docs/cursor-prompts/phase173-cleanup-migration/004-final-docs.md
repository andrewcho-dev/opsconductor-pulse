# Task 4: Comprehensive Documentation Update

This is the final documentation sweep for the entire Phases 166-173 effort. Every affected doc should be updated to reflect the complete template model.

## Files to Update

### 1. `docs/operations/database.md`

**Add/Update:**
- Migration history: add migrations 114-115
- Table reference: add all new tables (device_templates, template_metrics, template_commands, template_slots, device_modules, device_sensors, device_transports)
- Deprecated tables: document the `_deprecated_*` renamed tables and backward-compat views
- Data migration notes: describe the 114 migration logic (auto-assign templates, copy sensors/connections)

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add `173` to `phases` array
- Add migration files to `sources`

### 2. `docs/architecture/overview.md`

**Add/Update:**
- Device Template Model section (complete architecture diagram)
- Template → Instance relationship
- Metric normalization pipeline (raw keys → semantic keys)
- Deprecated systems (metric_catalog, normalized_metrics, metric_mappings)

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add `173` to `phases` array

### 3. `docs/api/customer-endpoints.md`

**Add/Update:**
- Complete Template API documentation (CRUD, sub-resources, clone)
- Updated Device API (template_id, modules, sensors, transports)
- Deprecated endpoints (device connections, legacy sensors)
- New telemetry endpoints (metric list, semantic key queries)

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add phases `166-173` to `phases` array

### 4. `docs/services/ingest.md`

**Add/Update:**
- MetricKeyMapCache documentation
- Normalization pipeline step
- Configuration env vars (METRIC_MAP_CACHE_TTL, METRIC_MAP_CACHE_SIZE)
- Prometheus metrics added

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add `172, 173` to `phases` array

### 5. `docs/services/ui-iot.md`

**Add/Update:**
- New route file: `routes/templates.py`
- Updated route files: `routes/devices.py`, `routes/sensors.py`, `routes/operator.py`
- New endpoints: modules, transports, template CRUD

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add `168, 169, 173` to `phases` array

### 6. `docs/features/device-management.md`

**Complete rewrite** to reflect the template model:
- Template system overview (system vs tenant, locked vs editable)
- Template definition (metrics, commands, slots)
- Device provisioning with templates (required sensor auto-creation)
- Module assignment (slot validation, compatible_templates, bus_address)
- Metric key normalization (metric_key_map on modules)
- Transport configuration (protocol vs connectivity separation)
- Device detail page (6-tab layout)
- Migration from legacy system

**Update frontmatter:**
- `last-verified: 2026-02-19`
- `phases: [166, 167, 168, 169, 170, 171, 172, 173]`
- Update `sources` to include all new files

### 7. `docs/development/frontend.md` (or equivalent)

**Add/Update:**
- New feature directory: `features/templates/`
- Updated device feature: new tab components, removed components
- New API service: `services/api/templates.ts`
- Updated types in `services/api/types.ts`
- Route changes in `app/router.tsx`

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add `170, 171, 173` to `phases` array

### 8. `docs/index.md`

**Add/Update:**
- Add "Device Templates" to the feature list
- Add links to template-related docs
- Note the deprecation of legacy metric systems

**Update frontmatter:**
- `last-verified: 2026-02-19`
- Add `173` to `phases` array

## For Each File

1. Read the current content completely
2. Update ALL sections affected by Phases 166-173
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-19`
   - Add relevant phase numbers to the `phases` array
   - Add/update `sources` to include new source files
4. Verify no stale information remains
5. Ensure cross-references between docs are consistent

## Final Verification Checklist

After updating all docs:
- [ ] No doc references `sensors` table without noting it's deprecated
- [ ] No doc references `device_connections` table without noting it's deprecated
- [ ] No doc references `normalized_metrics` or `metric_mappings` without noting deprecation
- [ ] Template model is consistently described across architecture, API, and feature docs
- [ ] All new endpoints are documented in API docs
- [ ] All new tables are documented in database docs
- [ ] All new frontend components are documented in development docs
- [ ] Migration notes explain the data flow from legacy to new tables

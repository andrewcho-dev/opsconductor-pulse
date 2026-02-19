# Task 4: Update Documentation

## Files to Update

### 1. `docs/operations/database.md`

Add documentation for:
- **device_modules** — Physical modules in slots, `metric_key_map` JSONB for raw→semantic key translation, unique constraint pattern with `COALESCE(bus_address, '')`
- **device_sensors** — Restructured from `sensors`, adds `template_metric_id`, `device_module_id`, `source` field (required/optional/unmodeled)
- **device_transports** — Replaces `device_connections`, separates `ingestion_protocol` from `physical_connectivity`, JSONB configs for each layer
- **device_registry changes** — New `template_id` and `parent_device_id` columns, parent validation trigger

Add migrations 111, 112, 113 to the migration history.

Note the data migration strategy: sensors → device_sensors (all as `source='unmodeled'`), device_connections → device_transports (infer `mqtt_direct` protocol).

### 2. `docs/architecture/overview.md`

Update the Device Template Model section to include instance-level tables and the relationship diagram.

### For Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 167 changes
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-19`
   - Add `167` to the `phases` array
   - Add `db/migrations/111_device_modules.sql`, `db/migrations/112_device_sensors_transports.sql`, `db/migrations/113_device_registry_template_fk.sql` to `sources`
4. Verify no stale information remains

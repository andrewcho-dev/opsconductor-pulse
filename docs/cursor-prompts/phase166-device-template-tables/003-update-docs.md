# Task 3: Update Documentation

## Files to Update

### 1. `docs/operations/database.md`

Add a new section documenting the device template tables:

- **device_templates** — Device type definitions (system or tenant-owned). Key columns: `tenant_id` (NULL = system), `is_locked`, `source`, `category`.
- **template_metrics** — Metric definitions per template. `is_required` flag controls auto-creation on device provisioning.
- **template_commands** — Command definitions per template with JSON Schema for parameters.
- **template_slots** — Expansion ports and bus interfaces. `interface_type` covers wired (analog, rs485, i2c, spi, 1-wire) and wireless (fsk, ble, lora). `compatible_templates` constrains which modules can be assigned.

Note the special RLS pattern: child tables (`template_metrics`, `template_commands`, `template_slots`) use EXISTS subqueries against the parent `device_templates` table.

Add migration 109 and 110 to the migration history section.

### 2. `docs/architecture/overview.md`

Add a "Device Template Model" subsection under the architecture section explaining:

- Templates define capability; instances define reality
- System templates (`tenant_id=NULL, is_locked=true`) vs tenant-owned templates
- Template hierarchy: device_templates → template_metrics + template_commands + template_slots
- `compatible_templates` on slots constrains module assignment (for Lifeline hardware)
- Same processing pipeline regardless of template source

### For Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 166 changes
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-19`
   - Add `166` to the `phases` array
   - Add `db/migrations/109_device_templates.sql` and `db/migrations/110_seed_device_templates.sql` to `sources`
4. Verify no stale information remains

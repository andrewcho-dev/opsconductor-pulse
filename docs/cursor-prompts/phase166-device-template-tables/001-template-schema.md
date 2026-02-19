# Task 1: Template Schema Migration (109)

## Create file: `db/migrations/109_device_templates.sql`

Write a SQL migration that creates 4 tables. Follow the exact patterns used in existing migrations (see `099_sensors_table.sql` and `106_carrier_integrations.sql` for reference).

## Table 1: `device_templates`

```sql
CREATE TABLE IF NOT EXISTS device_templates (
    id                      SERIAL PRIMARY KEY,
    tenant_id               TEXT REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name                    TEXT NOT NULL,
    slug                    TEXT NOT NULL,
    description             TEXT,
    category                TEXT NOT NULL CHECK (category IN (
        'gateway', 'edge_device', 'standalone_sensor', 'controller', 'expansion_module'
    )),
    manufacturer            TEXT,
    model                   TEXT,
    firmware_version_pattern TEXT,
    is_locked               BOOLEAN NOT NULL DEFAULT false,
    source                  TEXT NOT NULL DEFAULT 'tenant' CHECK (source IN ('system', 'tenant')),
    transport_defaults      JSONB,
    metadata                JSONB NOT NULL DEFAULT '{}',
    image_url               TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (tenant_id, slug)
);
```

**Important:** `tenant_id` is nullable. NULL means system template visible to all. The UNIQUE constraint on `(tenant_id, slug)` allows the same slug across different tenants but unique within each scope. PostgreSQL treats NULLs as distinct in unique constraints, so two system templates can't have the same slug — add a partial unique index:

```sql
CREATE UNIQUE INDEX idx_device_templates_system_slug
    ON device_templates (slug) WHERE tenant_id IS NULL;
```

### Indexes

```sql
CREATE INDEX idx_device_templates_tenant ON device_templates(tenant_id);
CREATE INDEX idx_device_templates_category ON device_templates(category);
CREATE INDEX idx_device_templates_source ON device_templates(source);
```

### RLS

This table needs a special RLS policy since `tenant_id` can be NULL (system templates visible to all):

```sql
ALTER TABLE device_templates ENABLE ROW LEVEL SECURITY;

-- Tenants see: system templates (tenant_id IS NULL) OR their own
CREATE POLICY device_templates_tenant_isolation ON device_templates
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)
    )
    WITH CHECK (
        tenant_id = current_setting('app.tenant_id', true)
    );

-- Operators can read all
CREATE POLICY device_templates_operator_read ON device_templates
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

-- Operators can write (for system templates)
CREATE POLICY device_templates_operator_write ON device_templates
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

-- Service access
CREATE POLICY device_templates_service ON device_templates
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');
```

### Grants

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON device_templates TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE device_templates_id_seq TO pulse_app;
```

### Updated_at trigger

Reuse the existing `update_sensors_timestamp()` trigger function from migration 099:

```sql
CREATE TRIGGER trg_device_templates_updated_at
    BEFORE UPDATE ON device_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();
```

---

## Table 2: `template_metrics`

```sql
CREATE TABLE IF NOT EXISTS template_metrics (
    id              SERIAL PRIMARY KEY,
    template_id     INT NOT NULL REFERENCES device_templates(id) ON DELETE CASCADE,
    metric_key      TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    data_type       TEXT NOT NULL CHECK (data_type IN ('float', 'integer', 'boolean', 'string', 'enum')),
    unit            TEXT,
    min_value       NUMERIC,
    max_value       NUMERIC,
    precision_digits INT NOT NULL DEFAULT 2,
    is_required     BOOLEAN NOT NULL DEFAULT false,
    description     TEXT,
    enum_values     JSONB,
    sort_order      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (template_id, metric_key)
);
```

### Indexes

```sql
CREATE INDEX idx_template_metrics_template ON template_metrics(template_id);
CREATE INDEX idx_template_metrics_required ON template_metrics(template_id, is_required) WHERE is_required = true;
```

### RLS

`template_metrics` inherits access control from its parent `device_templates` via the FK. But since RLS doesn't cascade automatically, apply a policy that joins through the parent:

```sql
ALTER TABLE template_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY template_metrics_tenant ON template_metrics
    USING (
        EXISTS (
            SELECT 1 FROM device_templates dt
            WHERE dt.id = template_metrics.template_id
            AND (dt.tenant_id IS NULL OR dt.tenant_id = current_setting('app.tenant_id', true))
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM device_templates dt
            WHERE dt.id = template_metrics.template_id
            AND dt.tenant_id = current_setting('app.tenant_id', true)
        )
    );

CREATE POLICY template_metrics_operator ON template_metrics
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

CREATE POLICY template_metrics_service ON template_metrics
    FOR ALL
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');
```

### Grants

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON template_metrics TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE template_metrics_id_seq TO pulse_app;
```

---

## Table 3: `template_commands`

```sql
CREATE TABLE IF NOT EXISTS template_commands (
    id                  SERIAL PRIMARY KEY,
    template_id         INT NOT NULL REFERENCES device_templates(id) ON DELETE CASCADE,
    command_key         TEXT NOT NULL,
    display_name        TEXT NOT NULL,
    description         TEXT,
    parameters_schema   JSONB,
    response_schema     JSONB,
    sort_order          INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (template_id, command_key)
);
```

### Indexes

```sql
CREATE INDEX idx_template_commands_template ON template_commands(template_id);
```

### RLS

Same pattern as `template_metrics` — policy via parent join:

```sql
ALTER TABLE template_commands ENABLE ROW LEVEL SECURITY;

CREATE POLICY template_commands_tenant ON template_commands
    USING (
        EXISTS (
            SELECT 1 FROM device_templates dt
            WHERE dt.id = template_commands.template_id
            AND (dt.tenant_id IS NULL OR dt.tenant_id = current_setting('app.tenant_id', true))
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM device_templates dt
            WHERE dt.id = template_commands.template_id
            AND dt.tenant_id = current_setting('app.tenant_id', true)
        )
    );

CREATE POLICY template_commands_operator ON template_commands
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

CREATE POLICY template_commands_service ON template_commands
    FOR ALL
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');
```

### Grants

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON template_commands TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE template_commands_id_seq TO pulse_app;
```

---

## Table 4: `template_slots`

```sql
CREATE TABLE IF NOT EXISTS template_slots (
    id                      SERIAL PRIMARY KEY,
    template_id             INT NOT NULL REFERENCES device_templates(id) ON DELETE CASCADE,
    slot_key                TEXT NOT NULL,
    display_name            TEXT NOT NULL,
    slot_type               TEXT NOT NULL CHECK (slot_type IN ('expansion', 'sensor', 'accessory')),
    interface_type          TEXT NOT NULL CHECK (interface_type IN (
        'analog', 'rs485', 'i2c', 'spi', '1-wire', 'fsk', 'ble', 'lora', 'gpio', 'usb'
    )),
    max_devices             INT DEFAULT 1,
    compatible_templates    INT[],
    is_required             BOOLEAN NOT NULL DEFAULT false,
    description             TEXT,
    sort_order              INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (template_id, slot_key)
);
```

### Indexes

```sql
CREATE INDEX idx_template_slots_template ON template_slots(template_id);
```

### RLS

Same parent-join pattern:

```sql
ALTER TABLE template_slots ENABLE ROW LEVEL SECURITY;

CREATE POLICY template_slots_tenant ON template_slots
    USING (
        EXISTS (
            SELECT 1 FROM device_templates dt
            WHERE dt.id = template_slots.template_id
            AND (dt.tenant_id IS NULL OR dt.tenant_id = current_setting('app.tenant_id', true))
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM device_templates dt
            WHERE dt.id = template_slots.template_id
            AND dt.tenant_id = current_setting('app.tenant_id', true)
        )
    );

CREATE POLICY template_slots_operator ON template_slots
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

CREATE POLICY template_slots_service ON template_slots
    FOR ALL
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');
```

### Grants

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON template_slots TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE template_slots_id_seq TO pulse_app;
```

---

## Comments

Add descriptive comments on key columns:

```sql
COMMENT ON TABLE device_templates IS 'Device type definitions — system (tenant_id=NULL, is_locked=true) or tenant-owned';
COMMENT ON COLUMN device_templates.slug IS 'URL-safe identifier, unique per tenant scope';
COMMENT ON COLUMN device_templates.firmware_version_pattern IS 'Regex or semver range for compatible firmware versions';
COMMENT ON COLUMN device_templates.transport_defaults IS 'Default ingestion_protocol and physical_connectivity as JSONB';

COMMENT ON TABLE template_metrics IS 'Metric definitions for a device template — what this device type can measure';
COMMENT ON COLUMN template_metrics.is_required IS 'If true, auto-created as device_sensor when device is provisioned with this template';
COMMENT ON COLUMN template_metrics.enum_values IS 'For data_type=enum: JSON array of allowed values, e.g. ["on","off","standby"]';

COMMENT ON TABLE template_commands IS 'Command definitions for a device template — what commands this device type accepts';
COMMENT ON COLUMN template_commands.parameters_schema IS 'JSON Schema for command parameters';

COMMENT ON TABLE template_slots IS 'Expansion slots and bus interfaces on a device template';
COMMENT ON COLUMN template_slots.interface_type IS 'Physical interface: analog, rs485, i2c, spi, 1-wire (wired) or fsk, ble, lora (wireless)';
COMMENT ON COLUMN template_slots.max_devices IS '1 for analog/gpio; N for bus/radio interfaces; NULL for unlimited';
COMMENT ON COLUMN template_slots.compatible_templates IS 'Array of device_template IDs (category=expansion_module) that can be assigned to this slot';
```

## Verification

```sql
-- Check all 4 tables exist
SELECT tablename FROM pg_tables WHERE tablename IN (
    'device_templates', 'template_metrics', 'template_commands', 'template_slots'
);

-- Check RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('device_templates', 'template_metrics', 'template_commands', 'template_slots');

-- Check policies
SELECT tablename, policyname FROM pg_policies
WHERE tablename IN ('device_templates', 'template_metrics', 'template_commands', 'template_slots')
ORDER BY tablename, policyname;
```

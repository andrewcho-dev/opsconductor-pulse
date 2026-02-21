-- Migration 109: Device templates and template sub-resources
-- Introduces the unified device template model:
-- - device_templates: system (tenant_id NULL) or tenant-owned (tenant_id set)
-- - template_metrics: metric definitions per template
-- - template_commands: command definitions per template
-- - template_slots: expansion/bus slots per template

BEGIN;

-- ============================================================
-- device_templates
-- ============================================================
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

-- For system templates (tenant_id IS NULL), enforce a single slug across the global scope.
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_templates_system_slug
    ON device_templates (slug) WHERE tenant_id IS NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_templates_tenant ON device_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_device_templates_category ON device_templates(category);
CREATE INDEX IF NOT EXISTS idx_device_templates_source ON device_templates(source);

-- Updated_at trigger
DROP TRIGGER IF EXISTS trg_device_templates_updated_at ON device_templates;
CREATE TRIGGER trg_device_templates_updated_at
    BEFORE UPDATE ON device_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();

-- RLS
ALTER TABLE device_templates ENABLE ROW LEVEL SECURITY;

-- Tenants can read: system templates (tenant_id IS NULL) OR their own.
-- Tenants can write: only their own (tenant_id must match).
DROP POLICY IF EXISTS device_templates_tenant_isolation ON device_templates;
CREATE POLICY device_templates_tenant_isolation ON device_templates
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)
    )
    WITH CHECK (
        tenant_id = current_setting('app.tenant_id', true)
    );

DROP POLICY IF EXISTS device_templates_operator_read ON device_templates;
CREATE POLICY device_templates_operator_read ON device_templates
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

DROP POLICY IF EXISTS device_templates_operator_write ON device_templates;
CREATE POLICY device_templates_operator_write ON device_templates
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

DROP POLICY IF EXISTS device_templates_service ON device_templates;
CREATE POLICY device_templates_service ON device_templates
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON device_templates TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON device_templates TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE device_templates_id_seq TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE device_templates_id_seq TO pulse_operator;

-- ============================================================
-- template_metrics
-- ============================================================
-- RLS: EXEMPT - no tenant_id column; tenant visibility enforced via device_templates join policies
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_template_metrics_template ON template_metrics(template_id);
CREATE INDEX IF NOT EXISTS idx_template_metrics_required
    ON template_metrics(template_id, is_required) WHERE is_required = true;

-- RLS (via parent join)
ALTER TABLE template_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS template_metrics_tenant ON template_metrics;
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

DROP POLICY IF EXISTS template_metrics_operator ON template_metrics;
CREATE POLICY template_metrics_operator ON template_metrics
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

DROP POLICY IF EXISTS template_metrics_service ON template_metrics;
CREATE POLICY template_metrics_service ON template_metrics
    FOR ALL
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON template_metrics TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON template_metrics TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE template_metrics_id_seq TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE template_metrics_id_seq TO pulse_operator;

-- ============================================================
-- template_commands
-- ============================================================
-- RLS: EXEMPT - no tenant_id column; tenant visibility enforced via device_templates join policies
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_template_commands_template ON template_commands(template_id);

-- RLS (via parent join)
ALTER TABLE template_commands ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS template_commands_tenant ON template_commands;
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

DROP POLICY IF EXISTS template_commands_operator ON template_commands;
CREATE POLICY template_commands_operator ON template_commands
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

DROP POLICY IF EXISTS template_commands_service ON template_commands;
CREATE POLICY template_commands_service ON template_commands
    FOR ALL
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON template_commands TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON template_commands TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE template_commands_id_seq TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE template_commands_id_seq TO pulse_operator;

-- ============================================================
-- template_slots
-- ============================================================
-- RLS: EXEMPT - no tenant_id column; tenant visibility enforced via device_templates join policies
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_template_slots_template ON template_slots(template_id);

-- RLS (via parent join)
ALTER TABLE template_slots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS template_slots_tenant ON template_slots;
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

DROP POLICY IF EXISTS template_slots_operator ON template_slots;
CREATE POLICY template_slots_operator ON template_slots
    FOR ALL
    USING (current_setting('app.role', true) = 'operator')
    WITH CHECK (current_setting('app.role', true) = 'operator');

DROP POLICY IF EXISTS template_slots_service ON template_slots;
CREATE POLICY template_slots_service ON template_slots
    FOR ALL
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON template_slots TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON template_slots TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE template_slots_id_seq TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE template_slots_id_seq TO pulse_operator;

-- ============================================================
-- Comments
-- ============================================================
COMMENT ON TABLE device_templates IS 'Device type definitions — system (tenant_id=NULL, is_locked=true) or tenant-owned';
COMMENT ON COLUMN device_templates.slug IS 'URL-safe identifier, unique per tenant scope';
COMMENT ON COLUMN device_templates.firmware_version_pattern IS 'Regex or semver range for compatible firmware versions';
COMMENT ON COLUMN device_templates.transport_defaults IS 'Default ingestion_protocol and physical_connectivity as JSONB';

COMMENT ON TABLE template_metrics IS 'Metric definitions for a device template — what this device type can measure';
COMMENT ON COLUMN template_metrics.is_required IS 'If true, auto-created as device_sensor when device is provisioned with this template';
COMMENT ON COLUMN template_metrics.enum_values IS 'For data_type=enum: JSON array of allowed values';

COMMENT ON TABLE template_commands IS 'Command definitions for a device template — what commands this device type accepts';
COMMENT ON COLUMN template_commands.parameters_schema IS 'JSON Schema for command parameters';

COMMENT ON TABLE template_slots IS 'Expansion slots and bus interfaces on a device template';
COMMENT ON COLUMN template_slots.interface_type IS 'Physical interface: analog/rs485/i2c/spi/1-wire or fsk/ble/lora';
COMMENT ON COLUMN template_slots.max_devices IS '1 for analog/gpio; N for bus/radio interfaces; NULL for unlimited';
COMMENT ON COLUMN template_slots.compatible_templates IS 'Array of device_template IDs (category=expansion_module) that can be assigned to this slot';

COMMIT;


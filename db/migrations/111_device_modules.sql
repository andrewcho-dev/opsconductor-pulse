-- Migration 111: Device modules (instance-level expansion modules)
-- Tracks which physical expansion modules are installed in which slots on a device.

BEGIN;

CREATE TABLE IF NOT EXISTS device_modules (
    id                  SERIAL PRIMARY KEY,
    tenant_id           TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    device_id           TEXT NOT NULL,
    slot_key            TEXT NOT NULL,
    bus_address         TEXT,
    module_template_id  INT REFERENCES device_templates(id) ON DELETE SET NULL,
    label               TEXT NOT NULL,
    serial_number       TEXT,
    metric_key_map      JSONB NOT NULL DEFAULT '{}',
    installed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'removed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- FK to device_registry (composite key)
    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry(tenant_id, device_id)
        ON DELETE CASCADE
);

-- Unique constraint: allow multiple per slot when bus_address differs, but enforce 1:1 when bus_address is NULL
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_modules_slot_address
    ON device_modules (tenant_id, device_id, slot_key, COALESCE(bus_address, ''));

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_modules_tenant_device ON device_modules(tenant_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_modules_template ON device_modules(module_template_id);
CREATE INDEX IF NOT EXISTS idx_device_modules_status ON device_modules(tenant_id, status);

-- RLS
ALTER TABLE device_modules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS device_modules_tenant_isolation ON device_modules;
CREATE POLICY device_modules_tenant_isolation ON device_modules
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

DROP POLICY IF EXISTS device_modules_operator_read ON device_modules;
CREATE POLICY device_modules_operator_read ON device_modules
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

DROP POLICY IF EXISTS device_modules_service ON device_modules;
CREATE POLICY device_modules_service ON device_modules
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON device_modules TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON device_modules TO pulse_operator;
GRANT USAGE, SELECT ON SEQUENCE device_modules_id_seq TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE device_modules_id_seq TO pulse_operator;

-- Trigger
DROP TRIGGER IF EXISTS trg_device_modules_updated_at ON device_modules;
CREATE TRIGGER trg_device_modules_updated_at
    BEFORE UPDATE ON device_modules
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();

-- Comments
COMMENT ON TABLE device_modules IS 'Physical expansion modules installed in device slots/bus interfaces';
COMMENT ON COLUMN device_modules.slot_key IS 'References template_slots.slot_key on the device template';
COMMENT ON COLUMN device_modules.bus_address IS 'Interface-specific address: 1-Wire ROM, Modbus slave ID, FSK radio ID, BLE MAC, I2C addr. NULL for analog (1:1 ports)';
COMMENT ON COLUMN device_modules.metric_key_map IS 'Maps raw firmware telemetry keys to semantic metric names, e.g. {\"port_3_temp\": \"temperature\"}';
COMMENT ON COLUMN device_modules.module_template_id IS 'FK to device_templates where category=expansion_module. Validated at application layer.';

COMMIT;


-- Migration 102: Expand device_registry with additional hardware identity fields
-- These fields enable positive identification of the exact physical unit,
-- its chipset, modem, firmware stack, and deployment context.

-- Hardware identity
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS chipset TEXT;
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS modem_model TEXT;
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS board_revision TEXT;
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS meid TEXT;              -- CDMA mobile equipment identifier

-- Firmware stack (fw_version already exists — add bootloader and modem firmware)
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS bootloader_version TEXT;
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS modem_fw_version TEXT;

-- Deployment context
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS deployment_date TIMESTAMPTZ;
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS batch_id TEXT;           -- Manufacturing batch/lot number
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS installation_notes TEXT;

-- Sensor limit per device (can be overridden from tier default)
ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS sensor_limit INT DEFAULT 20;

-- Reclassify device_type to be explicitly about the device role, not sensor type
-- Existing values: 'temperature', 'humidity', 'pressure', 'power', 'vibration', 'flow', 'level', 'gateway'
-- New convention: 'gateway', 'edge_device', 'standalone_sensor', 'controller'
-- We don't ALTER the existing column — seed data overhaul (task 006) will set correct values.

COMMENT ON COLUMN device_registry.device_type IS
    'Device role: gateway, edge_device, standalone_sensor, controller. NOT the sensor type.';
COMMENT ON COLUMN device_registry.sensor_limit IS
    'Maximum number of sensors this device can host. Defaults to 20. Can be overridden per-device from tier default.';
COMMENT ON COLUMN device_registry.chipset IS
    'SoC/chipset identifier (e.g., ESP32-S3, nRF9160, Quectel BG96)';
COMMENT ON COLUMN device_registry.modem_model IS
    'Cellular modem hardware model (e.g., Quectel EC25, Sierra MC7455)';
COMMENT ON COLUMN device_registry.board_revision IS
    'PCB board revision (e.g., "rev3.2", "v2.0-beta")';
COMMENT ON COLUMN device_registry.bootloader_version IS
    'Bootloader/U-Boot version running on the device';
COMMENT ON COLUMN device_registry.modem_fw_version IS
    'Cellular modem firmware version (separate from main application firmware)';
COMMENT ON COLUMN device_registry.deployment_date IS
    'Date the device was physically deployed/installed at its location';
COMMENT ON COLUMN device_registry.batch_id IS
    'Manufacturing batch or lot number for tracking hardware provenance';


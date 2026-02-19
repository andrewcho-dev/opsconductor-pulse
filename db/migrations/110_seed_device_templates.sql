-- Migration 110: Seed system device templates (Lifeline hardware)
-- System templates:
-- - tenant_id IS NULL
-- - is_locked = true
-- - source = 'system'

BEGIN;

-- ============================================================
-- 1. Lifeline Gateway v1
-- ============================================================
INSERT INTO device_templates (
    tenant_id,
    name,
    slug,
    description,
    category,
    manufacturer,
    model,
    is_locked,
    source,
    transport_defaults,
    metadata
)
VALUES (
    NULL,
    'Lifeline Gateway v1',
    'lifeline-gateway-v1',
    'Lifeline IoT gateway with expansion ports for analog sensors, 1-Wire bus, and FSK radio link. Placeholder — port count and interface types will be refined when hardware is finalized.',
    'gateway',
    'Lifeline',
    'GW-V1',
    true,
    'system',
    '{"ingestion_protocol": "mqtt_direct", "physical_connectivity": "cellular"}'::jsonb,
    '{}'::jsonb
)
ON CONFLICT DO NOTHING;

-- Gateway required metrics
INSERT INTO template_metrics (
    template_id,
    metric_key,
    display_name,
    data_type,
    unit,
    min_value,
    max_value,
    precision_digits,
    is_required,
    description,
    sort_order
)
SELECT dt.id,
       v.metric_key,
       v.display_name,
       v.data_type,
       v.unit,
       v.min_value,
       v.max_value,
       v.precision_digits,
       v.is_required,
       v.description,
       v.sort_order
FROM device_templates dt,
     (VALUES
        ('battery_pct',    'Battery Level',    'float',   '%',    0::numeric,     100::numeric, 1, true,  'Battery charge percentage', 1),
        ('signal_rssi',    'Signal Strength',  'integer', 'dBm', -120::numeric,    0::numeric,  0, true,  'Cellular signal RSSI',      2),
        ('uptime_seconds', 'Uptime',           'integer', 's',    0::numeric,   NULL::numeric,  0, true,  'Seconds since last boot',   3),
        ('cpu_temp',       'CPU Temperature',  'float',   'degC', -40::numeric,   85::numeric,  1, false, 'Processor temperature',     4),
        ('memory_pct',     'Memory Usage',     'float',   '%',    0::numeric,    100::numeric,  1, false, 'RAM usage percentage',      5),
        ('supply_voltage', 'Supply Voltage',   'float',   'V',    0::numeric,     30::numeric,  2, false, 'Input supply voltage',      6)
     ) AS v(metric_key, display_name, data_type, unit, min_value, max_value, precision_digits, is_required, description, sort_order)
WHERE dt.slug = 'lifeline-gateway-v1'
  AND dt.tenant_id IS NULL
ON CONFLICT (template_id, metric_key) DO NOTHING;

-- Gateway commands
INSERT INTO template_commands (
    template_id,
    command_key,
    display_name,
    description,
    parameters_schema,
    sort_order
)
SELECT dt.id,
       v.command_key,
       v.display_name,
       v.description,
       v.parameters_schema::jsonb,
       v.sort_order
FROM device_templates dt,
     (VALUES
        ('reboot',        'Reboot',              'Restart the gateway',
         '{"type":"object","properties":{}}', 1),
        ('set_interval',  'Set Report Interval', 'Change telemetry reporting interval',
         '{"type":"object","properties":{"interval_seconds":{"type":"integer","minimum":10,"maximum":86400}},"required":["interval_seconds"]}', 2),
        ('factory_reset', 'Factory Reset',       'Reset to factory defaults (WARNING: clears all local config)',
         '{"type":"object","properties":{"confirm":{"type":"boolean","const":true}},"required":["confirm"]}', 3)
     ) AS v(command_key, display_name, description, parameters_schema, sort_order)
WHERE dt.slug = 'lifeline-gateway-v1'
  AND dt.tenant_id IS NULL
ON CONFLICT (template_id, command_key) DO NOTHING;

-- ============================================================
-- 2. Lifeline Temperature Probe (expansion module)
-- ============================================================
INSERT INTO device_templates (
    tenant_id, name, slug, description, category, manufacturer, model, is_locked, source, metadata
)
VALUES (
    NULL,
    'Lifeline Temperature Probe',
    'lifeline-temp-probe',
    'Single-point temperature sensor for analog or 1-Wire connection.',
    'expansion_module',
    'Lifeline',
    'TP-100',
    true,
    'system',
    '{}'::jsonb
)
ON CONFLICT DO NOTHING;

INSERT INTO template_metrics (
    template_id, metric_key, display_name, data_type, unit, min_value, max_value,
    precision_digits, is_required, description, sort_order
)
SELECT dt.id,
       v.metric_key,
       v.display_name,
       v.data_type,
       v.unit,
       v.min_value,
       v.max_value,
       v.precision_digits,
       v.is_required,
       v.description,
       v.sort_order
FROM device_templates dt,
     (VALUES
        ('temperature', 'Temperature', 'float', 'degC', -40::numeric, 125::numeric, 1, true, 'Measured temperature', 1)
     ) AS v(metric_key, display_name, data_type, unit, min_value, max_value, precision_digits, is_required, description, sort_order)
WHERE dt.slug = 'lifeline-temp-probe'
  AND dt.tenant_id IS NULL
ON CONFLICT (template_id, metric_key) DO NOTHING;

-- ============================================================
-- 3. Lifeline Humidity Sensor (expansion module)
-- ============================================================
INSERT INTO device_templates (
    tenant_id, name, slug, description, category, manufacturer, model, is_locked, source, metadata
)
VALUES (
    NULL,
    'Lifeline Humidity Sensor',
    'lifeline-humidity-sensor',
    'Combined humidity and temperature sensor module.',
    'expansion_module',
    'Lifeline',
    'HT-200',
    true,
    'system',
    '{}'::jsonb
)
ON CONFLICT DO NOTHING;

INSERT INTO template_metrics (
    template_id, metric_key, display_name, data_type, unit, min_value, max_value,
    precision_digits, is_required, description, sort_order
)
SELECT dt.id,
       v.metric_key,
       v.display_name,
       v.data_type,
       v.unit,
       v.min_value,
       v.max_value,
       v.precision_digits,
       v.is_required,
       v.description,
       v.sort_order
FROM device_templates dt,
     (VALUES
        ('humidity',    'Humidity',    'float', '%',    0::numeric, 100::numeric, 1, true, 'Relative humidity',   1),
        ('temperature', 'Temperature', 'float', 'degC', -40::numeric, 85::numeric, 1, true, 'Ambient temperature', 2)
     ) AS v(metric_key, display_name, data_type, unit, min_value, max_value, precision_digits, is_required, description, sort_order)
WHERE dt.slug = 'lifeline-humidity-sensor'
  AND dt.tenant_id IS NULL
ON CONFLICT (template_id, metric_key) DO NOTHING;

-- ============================================================
-- 4. Lifeline GPS Tracker (expansion module)
-- ============================================================
INSERT INTO device_templates (
    tenant_id, name, slug, description, category, manufacturer, model, is_locked, source, metadata
)
VALUES (
    NULL,
    'Lifeline GPS Tracker',
    'lifeline-gps-tracker',
    'GPS/GNSS position tracking module.',
    'expansion_module',
    'Lifeline',
    'GPS-300',
    true,
    'system',
    '{}'::jsonb
)
ON CONFLICT DO NOTHING;

INSERT INTO template_metrics (
    template_id, metric_key, display_name, data_type, unit, min_value, max_value,
    precision_digits, is_required, description, sort_order
)
SELECT dt.id,
       v.metric_key,
       v.display_name,
       v.data_type,
       v.unit,
       v.min_value,
       v.max_value,
       v.precision_digits,
       v.is_required,
       v.description,
       v.sort_order
FROM device_templates dt,
     (VALUES
        ('latitude',  'Latitude',  'float',   'deg', -90::numeric,   90::numeric,  6, true, 'GPS latitude',    1),
        ('longitude', 'Longitude', 'float',   'deg', -180::numeric, 180::numeric, 6, true, 'GPS longitude',   2),
        ('speed',     'Speed',     'float',   'km/h', 0::numeric,   500::numeric, 1, true, 'Ground speed',    3),
        ('heading',   'Heading',   'float',   'deg', 0::numeric,    360::numeric, 1, true, 'Compass heading', 4)
     ) AS v(metric_key, display_name, data_type, unit, min_value, max_value, precision_digits, is_required, description, sort_order)
WHERE dt.slug = 'lifeline-gps-tracker'
  AND dt.tenant_id IS NULL
ON CONFLICT (template_id, metric_key) DO NOTHING;

-- ============================================================
-- 5. Gateway template_slots (expansion ports)
-- ============================================================
INSERT INTO template_slots (
    template_id, slot_key, display_name, slot_type, interface_type, max_devices,
    is_required, description, sort_order
)
SELECT dt.id,
       v.slot_key,
       v.display_name,
       v.slot_type,
       v.interface_type,
       v.max_devices,
       v.is_required,
       v.description,
       v.sort_order
FROM device_templates dt,
     (VALUES
        ('analog_1',  'Analog Port 1',  'expansion', 'analog', 1, false, 'Analog input port 1 (0-10V or 4-20mA)', 1),
        ('analog_2',  'Analog Port 2',  'expansion', 'analog', 1, false, 'Analog input port 2 (0-10V or 4-20mA)', 2),
        ('onewire_1', '1-Wire Bus',     'expansion', '1-wire', 8, false, '1-Wire digital bus — up to 8 sensors',   3),
        ('fsk_radio', 'FSK Radio Link', 'expansion', 'fsk',    4, false, 'FSK radio link — up to 4 modules',       4)
     ) AS v(slot_key, display_name, slot_type, interface_type, max_devices, is_required, description, sort_order)
WHERE dt.slug = 'lifeline-gateway-v1'
  AND dt.tenant_id IS NULL
ON CONFLICT (template_id, slot_key) DO NOTHING;

-- ============================================================
-- 6. Set compatible_templates on gateway slots
-- ============================================================
UPDATE template_slots
SET compatible_templates = ARRAY(
    SELECT id FROM device_templates
    WHERE slug IN ('lifeline-temp-probe')
      AND tenant_id IS NULL
    ORDER BY id
)
WHERE slot_key IN ('analog_1', 'analog_2')
  AND template_id = (
    SELECT id FROM device_templates
    WHERE slug = 'lifeline-gateway-v1' AND tenant_id IS NULL
  );

UPDATE template_slots
SET compatible_templates = ARRAY(
    SELECT id FROM device_templates
    WHERE slug IN ('lifeline-temp-probe', 'lifeline-humidity-sensor')
      AND tenant_id IS NULL
    ORDER BY id
)
WHERE slot_key = 'onewire_1'
  AND template_id = (
    SELECT id FROM device_templates
    WHERE slug = 'lifeline-gateway-v1' AND tenant_id IS NULL
  );

UPDATE template_slots
SET compatible_templates = ARRAY(
    SELECT id FROM device_templates
    WHERE category = 'expansion_module'
      AND tenant_id IS NULL
    ORDER BY id
)
WHERE slot_key = 'fsk_radio'
  AND template_id = (
    SELECT id FROM device_templates
    WHERE slug = 'lifeline-gateway-v1' AND tenant_id IS NULL
  );

COMMIT;


-- Migration 104: Replace flat SENSOR-* records with proper gateway → sensor hierarchy
-- Deletes old seed data and creates realistic gateway + sensor + connection + health records.

-- =============================================================
-- STEP 1: Clean up old seed data (acme-industrial tenant only)
-- =============================================================

-- Delete old telemetry for old device IDs
DELETE FROM telemetry
WHERE tenant_id = 'acme-industrial'
  AND device_id LIKE 'SENSOR-%';

-- Delete old device state
DELETE FROM device_state
WHERE tenant_id = 'acme-industrial'
  AND device_id LIKE 'SENSOR-%';

-- Delete old device tags
DELETE FROM device_tags
WHERE tenant_id = 'acme-industrial'
  AND device_id LIKE 'SENSOR-%';

-- Delete old device extended attributes
DELETE FROM device_extended_attributes
WHERE tenant_id = 'acme-industrial'
  AND device_id LIKE 'SENSOR-%';

-- Delete old devices (CASCADE will clean up most FKs)
DELETE FROM device_registry
WHERE tenant_id = 'acme-industrial'
  AND device_id LIKE 'SENSOR-%';


-- =============================================================
-- STEP 2: Create gateway devices
-- =============================================================

INSERT INTO device_registry (
    tenant_id, device_id, site_id, status, device_type,
    model, manufacturer, chipset, modem_model,
    serial_number, mac_address, imei, iccid,
    hw_revision, board_revision, fw_version, bootloader_version, modem_fw_version,
    batch_id, deployment_date, sensor_limit, notes,
    created_at
) VALUES
-- Gateway 1: Building A - Server Room & HVAC monitoring
(
    'acme-industrial', 'GW-001', 'acme-hq', 'ACTIVE', 'gateway',
    'EdgeGate EG-200', 'SimCloud Devices', 'nRF9160', 'Quectel BG96',
    'EG200-2024-00142', 'A4:CF:12:B8:3E:01', '352656100142001', '8901260012345678901',
    'v2.1', 'rev3.2', '2.4.1', '1.2.0', 'BG96MAR02A07M1G',
    'BATCH-2024-Q1-042', now() - INTERVAL '18 months', 10,
    'Primary gateway for Building A environmental monitoring',
    now() - INTERVAL '18 months'
),
-- Gateway 2: Building B - Lab & Machinery monitoring
(
    'acme-industrial', 'GW-002', 'acme-hq', 'ACTIVE', 'gateway',
    'EdgeGate EG-200', 'SimCloud Devices', 'nRF9160', 'Quectel BG96',
    'EG200-2024-00187', 'A4:CF:12:B8:3E:02', '352656100187002', '8901260012345678902',
    'v2.1', 'rev3.2', '2.4.1', '1.2.0', 'BG96MAR02A07M1G',
    'BATCH-2024-Q1-042', now() - INTERVAL '12 months', 10,
    'Lab and machinery monitoring gateway',
    now() - INTERVAL '12 months'
),
-- Gateway 3: Building C - New Wing (recently deployed, fewer sensors)
(
    'acme-industrial', 'GW-003', 'acme-hq', 'ACTIVE', 'gateway',
    'EdgeGate EG-100', 'SimCloud Devices', 'ESP32-S3', 'Sierra MC7455',
    'EG100-2025-00031', 'A4:CF:12:B8:3E:03', '352656100031003', '8901260012345678903',
    'v1.0', 'rev1.1', '1.8.3', '1.0.0', 'SWI9X30C_02.33.03.00',
    'BATCH-2025-Q1-008', now() - INTERVAL '2 months', 5,
    'New wing pilot deployment — limited sensor loadout',
    now() - INTERVAL '2 months'
),
-- Gateway 4: Building A - Power & Electrical (industrial grade)
(
    'acme-industrial', 'GW-004', 'acme-hq', 'ACTIVE', 'gateway',
    'IndustrialEdge IE-500', 'SimCloud Devices', 'AM6254', 'Quectel EC25',
    'IE500-2023-00089', 'A4:CF:12:B8:3E:04', '352656100089004', '8901260012345678904',
    'v3.0', 'rev5.0', '3.1.0', '2.0.1', 'EC25EFAR06A06M4G',
    'BATCH-2023-Q3-015', now() - INTERVAL '24 months', 20,
    'Industrial-grade gateway for power monitoring and electrical systems',
    now() - INTERVAL '24 months'
);


-- =============================================================
-- STEP 3: Create device_state records for gateways
-- =============================================================

INSERT INTO device_state (tenant_id, site_id, device_id, status, last_heartbeat_at, last_telemetry_at, last_seen_at)
VALUES
('acme-industrial', 'acme-hq', 'GW-001', 'ONLINE',  now() - INTERVAL '30 seconds', now() - INTERVAL '1 minute',  now() - INTERVAL '30 seconds'),
('acme-industrial', 'acme-hq', 'GW-002', 'ONLINE',  now() - INTERVAL '45 seconds', now() - INTERVAL '2 minutes', now() - INTERVAL '45 seconds'),
('acme-industrial', 'acme-hq', 'GW-003', 'STALE',   now() - INTERVAL '15 minutes', now() - INTERVAL '20 minutes', now() - INTERVAL '15 minutes'),
('acme-industrial', 'acme-hq', 'GW-004', 'ONLINE',  now() - INTERVAL '1 minute',   now() - INTERVAL '1 minute',  now() - INTERVAL '1 minute');


-- =============================================================
-- STEP 4: Create cellular connections for each gateway
-- =============================================================

INSERT INTO device_connections (
    tenant_id, device_id, connection_type,
    carrier_name, carrier_account_id, plan_name, apn,
    sim_iccid, sim_status,
    data_limit_mb, billing_cycle_start, data_used_mb, data_used_updated_at,
    ip_address, network_status, last_network_attach
) VALUES
(
    'acme-industrial', 'GW-001', 'cellular',
    'Hologram', 'HOL-ACME-2024-001', 'IoT Pro 500MB', 'hologram',
    '8901260012345678901', 'active',
    500, 1, 127.4, now() - INTERVAL '2 hours',
    '10.176.42.101'::INET, 'connected', now() - INTERVAL '3 days'
),
(
    'acme-industrial', 'GW-002', 'cellular',
    'Hologram', 'HOL-ACME-2024-001', 'IoT Pro 500MB', 'hologram',
    '8901260012345678902', 'active',
    500, 1, 203.8, now() - INTERVAL '2 hours',
    '10.176.42.102'::INET, 'connected', now() - INTERVAL '5 days'
),
(
    'acme-industrial', 'GW-003', 'cellular',
    '1NCE', '1NCE-ACME-2025-001', '1NCE IoT Flat Rate', '10piot.1nce.net',
    '8901260012345678903', 'active',
    500, 15, 12.1, now() - INTERVAL '6 hours',
    '10.176.42.103'::INET, 'disconnected', now() - INTERVAL '15 minutes'
),
(
    'acme-industrial', 'GW-004', 'cellular',
    'Hologram', 'HOL-ACME-2024-001', 'IoT Enterprise 2GB', 'hologram',
    '8901260012345678904', 'active',
    2048, 1, 847.2, now() - INTERVAL '1 hour',
    '10.176.42.104'::INET, 'connected', now() - INTERVAL '14 days'
);


-- =============================================================
-- STEP 5: Create sensors for each gateway
-- =============================================================

INSERT INTO sensors (
    tenant_id, device_id, metric_name, sensor_type, label, unit,
    min_range, max_range, precision_digits, status, auto_discovered,
    last_value, last_seen_at
) VALUES
-- GW-001 sensors (Building A: Server Room & HVAC - 5 sensors)
('acme-industrial', 'GW-001', 'temperature',     'temperature', 'Server Room Temperature',  '°C',    -10, 60,   1, 'active', true,  22.4, now() - INTERVAL '1 minute'),
('acme-industrial', 'GW-001', 'humidity',         'humidity',    'Server Room Humidity',     '%RH',    0,  100,  1, 'active', true,  45.2, now() - INTERVAL '1 minute'),
('acme-industrial', 'GW-001', 'pressure',         'pressure',    'Barometric Pressure',      'hPa',   800, 1200, 1, 'active', true,  1013.2, now() - INTERVAL '1 minute'),
('acme-industrial', 'GW-001', 'hvac_supply_temp', 'temperature', 'HVAC Supply Air Temp',     '°C',    -10, 50,   1, 'active', true,  14.8, now() - INTERVAL '2 minutes'),
('acme-industrial', 'GW-001', 'hvac_return_temp', 'temperature', 'HVAC Return Air Temp',     '°C',    -10, 50,   1, 'active', true,  23.1, now() - INTERVAL '2 minutes'),

-- GW-002 sensors (Building B: Lab & Machinery - 5 sensors)
('acme-industrial', 'GW-002', 'temperature',      'temperature', 'Lab Temperature',          '°C',    -10, 60,   1, 'active', true,  21.7, now() - INTERVAL '2 minutes'),
('acme-industrial', 'GW-002', 'humidity',          'humidity',    'Lab Humidity',             '%RH',    0,  100,  1, 'active', true,  52.8, now() - INTERVAL '2 minutes'),
('acme-industrial', 'GW-002', 'vibration_rms',     'vibration',   'CNC Machine Vibration',    'mm/s',   0,  50,   2, 'active', true,   2.34, now() - INTERVAL '2 minutes'),
('acme-industrial', 'GW-002', 'vibration_peak',    'vibration',   'CNC Machine Peak Vib',     'mm/s',   0,  100,  2, 'active', true,   4.87, now() - INTERVAL '2 minutes'),
('acme-industrial', 'GW-002', 'flow_rate',         'flow',        'Coolant Flow Rate',        'L/min',  0,  200,  1, 'active', true,  34.5, now() - INTERVAL '3 minutes'),

-- GW-003 sensors (Building C: New Wing - 2 sensors, newly deployed)
('acme-industrial', 'GW-003', 'temperature',       'temperature', 'New Wing Temperature',     '°C',    -10, 60,   1, 'active', true,  20.1, now() - INTERVAL '20 minutes'),
('acme-industrial', 'GW-003', 'humidity',           'humidity',    'New Wing Humidity',        '%RH',    0,  100,  1, 'active', true,  58.3, now() - INTERVAL '20 minutes'),

-- GW-004 sensors (Building A: Power & Electrical - 4 sensors)
('acme-industrial', 'GW-004', 'power_kw',          'power',       'Main Panel Active Power',   'kW',    0,  500,  2, 'active', true, 142.7, now() - INTERVAL '1 minute'),
('acme-industrial', 'GW-004', 'power_factor',       'power',       'Main Panel Power Factor',   '',      0,  1,    3, 'active', true,   0.923, now() - INTERVAL '1 minute'),
('acme-industrial', 'GW-004', 'voltage_l1',         'electrical',  'Phase L1 Voltage',          'V',   180, 260,  1, 'active', true, 237.4, now() - INTERVAL '1 minute'),
('acme-industrial', 'GW-004', 'current_total',      'electrical',  'Total Current Draw',        'A',     0, 1000, 1, 'active', true, 198.3, now() - INTERVAL '1 minute');


-- =============================================================
-- STEP 6: Seed device_health_telemetry (last 2 data points per gateway)
-- =============================================================

INSERT INTO device_health_telemetry (
    time, tenant_id, device_id,
    rssi, signal_quality, network_type, battery_pct, battery_voltage, power_source,
    cpu_temp_c, memory_used_pct, storage_used_pct, uptime_seconds, reboot_count,
    data_tx_bytes, data_rx_bytes, gps_lat, gps_lon, gps_fix
) VALUES
-- GW-001 (good signal, line powered, healthy)
(now() - INTERVAL '1 minute',  'acme-industrial', 'GW-001', -67, 78, 'LTE-M', NULL, NULL, 'line',   42.3, 34, 18, 2592000, 2,  524288, 1048576, 41.8781, -87.6298, true),
(now() - INTERVAL '6 minutes', 'acme-industrial', 'GW-001', -69, 75, 'LTE-M', NULL, NULL, 'line',   41.8, 33, 18, 2591700, 2,  512000, 1024000, 41.8781, -87.6298, true),
-- GW-002 (decent signal, line powered, moderate load)
(now() - INTERVAL '2 minutes', 'acme-industrial', 'GW-002', -78, 62, '4G',    NULL, NULL, 'line',   48.1, 52, 22, 864000,  5,  786432, 1572864, 41.8782, -87.6295, true),
(now() - INTERVAL '7 minutes', 'acme-industrial', 'GW-002', -76, 64, '4G',    NULL, NULL, 'line',   47.5, 51, 22, 863700,  5,  768000, 1536000, 41.8782, -87.6295, true),
-- GW-003 (weak signal, battery powered, stale)
(now() - INTERVAL '15 minutes','acme-industrial', 'GW-003', -98, 28, 'NB-IoT', 34,  3.42, 'battery', 31.2, 22, 8, 172800, 12,  32768,  65536,  41.8785, -87.6290, true),
(now() - INTERVAL '20 minutes','acme-industrial', 'GW-003', -96, 31, 'NB-IoT', 35,  3.44, 'battery', 30.8, 21, 8, 172500, 12,  30000,  60000,  41.8785, -87.6290, true),
-- GW-004 (strong signal, line powered, heavy workload)
(now() - INTERVAL '1 minute',  'acme-industrial', 'GW-004', -55, 92, '4G',    NULL, NULL, 'poe',    55.7, 68, 41, 5184000, 1, 2097152, 4194304, 41.8780, -87.6300, true),
(now() - INTERVAL '6 minutes', 'acme-industrial', 'GW-004', -54, 93, '4G',    NULL, NULL, 'poe',    55.2, 67, 41, 5183700, 1, 2048000, 4096000, 41.8780, -87.6300, true);


-- =============================================================
-- STEP 7: Device tags for new gateways
-- =============================================================

INSERT INTO device_tags (tenant_id, device_id, tag) VALUES
('acme-industrial', 'GW-001', 'building-a'),
('acme-industrial', 'GW-001', 'environment'),
('acme-industrial', 'GW-001', 'hvac'),
('acme-industrial', 'GW-002', 'building-b'),
('acme-industrial', 'GW-002', 'lab'),
('acme-industrial', 'GW-002', 'machinery'),
('acme-industrial', 'GW-003', 'building-c'),
('acme-industrial', 'GW-003', 'pilot'),
('acme-industrial', 'GW-004', 'building-a'),
('acme-industrial', 'GW-004', 'power'),
('acme-industrial', 'GW-004', 'electrical');


-- =============================================================
-- STEP 8: Update subscription active_device_count
-- =============================================================

UPDATE subscriptions
SET active_device_count = 4,
    updated_at = now()
WHERE subscription_id = 'sub-acme-main-001';


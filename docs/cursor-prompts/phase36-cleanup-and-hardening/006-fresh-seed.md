# 006: Fresh Test Data Seed

## Task

Seed a clean, realistic test environment with one tenant, one site, and 12 devices.

## Prerequisites

- Database cleaned (002-database-cleanup.md)
- Simulators stopped (001-stop-simulators.md)

## Seed Data

### Tenant

| Field | Value |
|-------|-------|
| tenant_id | `acme-industrial` |
| name | `Acme Industrial` |
| status | `ACTIVE` |

### Site

| Field | Value |
|-------|-------|
| site_id | `acme-hq` |
| name | `HQ` |
| location | `Chicago, IL` |
| latitude | `41.8781` |
| longitude | `-87.6298` |

### Subscription

| Field | Value |
|-------|-------|
| Type | `MAIN` |
| Device limit | `25` |
| Status | `ACTIVE` |
| Term | 1 year from today |

### Devices (12 total)

| Device ID | Type | Model | Status | Location | Building |
|-----------|------|-------|--------|----------|----------|
| SENSOR-001 | temperature | Tempix T200 | ACTIVE | Server Room | A |
| SENSOR-002 | temperature | Tempix T200 | ACTIVE | Warehouse | A |
| SENSOR-003 | humidity | HumidPro H50 | ACTIVE | Server Room | A |
| SENSOR-004 | pressure | BaroSense P100 | ACTIVE | Lab | B |
| SENSOR-005 | temperature | Tempix T200 | ACTIVE | Lab | B |
| SENSOR-006 | power | PowerMeter PM3000 | ACTIVE | Electrical | A |
| SENSOR-007 | vibration | VibeTech V400 | ACTIVE | Machinery | B |
| SENSOR-008 | temperature | Tempix T100 | INACTIVE | Storage | C |
| SENSOR-009 | flow | FlowMax F200 | ACTIVE | HVAC | A |
| SENSOR-010 | level | TankLevel TL50 | ACTIVE | Tank Farm | B |
| SENSOR-011 | temperature | Tempix T200 | PROVISIONED | New Wing | C |
| SENSOR-012 | gateway | EdgeGate EG100 | ACTIVE | Network Closet | A |

## Seed Migration

**File:** `db/migrations/052_seed_test_data.sql`

```sql
-- ============================================
-- Migration: 052_seed_test_data.sql
-- Purpose: Seed fresh test data
-- ============================================

BEGIN;

-- ============================================
-- 1. Tenant
-- ============================================

INSERT INTO tenants (tenant_id, name, status, created_at)
VALUES (
    'acme-industrial',
    'Acme Industrial',
    'ACTIVE',
    now()
)
ON CONFLICT (tenant_id) DO UPDATE
SET name = EXCLUDED.name, status = EXCLUDED.status;

-- ============================================
-- 2. Site
-- ============================================

INSERT INTO sites (site_id, tenant_id, name, location, latitude, longitude, created_at)
VALUES (
    'acme-hq',
    'acme-industrial',
    'HQ',
    'Chicago, IL',
    41.8781,
    -87.6298,
    now()
)
ON CONFLICT (site_id) DO UPDATE
SET name = EXCLUDED.name, location = EXCLUDED.location;

-- ============================================
-- 3. Subscription
-- ============================================

INSERT INTO subscriptions (
    subscription_id,
    tenant_id,
    subscription_type,
    device_limit,
    active_device_count,
    term_start,
    term_end,
    status,
    created_at
)
VALUES (
    'sub-acme-main-001',
    'acme-industrial',
    'MAIN',
    25,
    0,  -- Will be updated after devices
    now(),
    now() + interval '1 year',
    'ACTIVE',
    now()
)
ON CONFLICT (subscription_id) DO UPDATE
SET device_limit = EXCLUDED.device_limit,
    term_end = EXCLUDED.term_end,
    status = EXCLUDED.status;

-- ============================================
-- 4. Devices
-- ============================================

-- Device 1: Server Room Temperature
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-001', 'acme-industrial', 'acme-hq', 'temperature', 'Tempix T200', 'ACTIVE', now() - interval '18 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-001', 'acme-industrial',
    '{
        "manufacturer": "Tempix",
        "model": "T200",
        "firmware_version": "2.4.1",
        "install_date": "2023-06-15",
        "location": "Building A - Server Room",
        "latitude": 41.8783,
        "longitude": -87.6295,
        "maintenance_interval_days": 90,
        "last_calibration": "2024-09-01"
    }'::jsonb
);

-- Device 2: Warehouse Temperature
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-002', 'acme-industrial', 'acme-hq', 'temperature', 'Tempix T200', 'ACTIVE', now() - interval '15 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-002', 'acme-industrial',
    '{
        "manufacturer": "Tempix",
        "model": "T200",
        "firmware_version": "2.4.1",
        "install_date": "2023-09-20",
        "location": "Building A - Warehouse",
        "latitude": 41.8785,
        "longitude": -87.6292,
        "maintenance_interval_days": 90,
        "last_calibration": "2024-10-15"
    }'::jsonb
);

-- Device 3: Server Room Humidity
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-003', 'acme-industrial', 'acme-hq', 'humidity', 'HumidPro H50', 'ACTIVE', now() - interval '18 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-003', 'acme-industrial',
    '{
        "manufacturer": "HumidPro",
        "model": "H50",
        "firmware_version": "1.8.0",
        "install_date": "2023-06-15",
        "location": "Building A - Server Room",
        "latitude": 41.8783,
        "longitude": -87.6295,
        "maintenance_interval_days": 60,
        "last_calibration": "2024-11-01"
    }'::jsonb
);

-- Device 4: Lab Pressure
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-004', 'acme-industrial', 'acme-hq', 'pressure', 'BaroSense P100', 'ACTIVE', now() - interval '12 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-004', 'acme-industrial',
    '{
        "manufacturer": "BaroSense",
        "model": "P100",
        "firmware_version": "3.1.2",
        "install_date": "2024-01-10",
        "location": "Building B - Lab",
        "latitude": 41.8778,
        "longitude": -87.6302,
        "maintenance_interval_days": 30,
        "last_calibration": "2024-12-01"
    }'::jsonb
);

-- Device 5: Lab Temperature
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-005', 'acme-industrial', 'acme-hq', 'temperature', 'Tempix T200', 'ACTIVE', now() - interval '12 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-005', 'acme-industrial',
    '{
        "manufacturer": "Tempix",
        "model": "T200",
        "firmware_version": "2.4.1",
        "install_date": "2024-01-10",
        "location": "Building B - Lab",
        "latitude": 41.8778,
        "longitude": -87.6302,
        "maintenance_interval_days": 90,
        "last_calibration": "2024-10-01"
    }'::jsonb
);

-- Device 6: Electrical Power Meter
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-006', 'acme-industrial', 'acme-hq', 'power', 'PowerMeter PM3000', 'ACTIVE', now() - interval '24 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-006', 'acme-industrial',
    '{
        "manufacturer": "PowerMeter",
        "model": "PM3000",
        "firmware_version": "4.0.5",
        "install_date": "2022-12-01",
        "location": "Building A - Electrical Room",
        "latitude": 41.8782,
        "longitude": -87.6300,
        "maintenance_interval_days": 180,
        "last_calibration": "2024-06-01",
        "rated_voltage": 480,
        "rated_current": 200
    }'::jsonb
);

-- Device 7: Machinery Vibration
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-007', 'acme-industrial', 'acme-hq', 'vibration', 'VibeTech V400', 'ACTIVE', now() - interval '8 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-007', 'acme-industrial',
    '{
        "manufacturer": "VibeTech",
        "model": "V400",
        "firmware_version": "2.2.0",
        "install_date": "2024-05-15",
        "location": "Building B - Machinery Hall",
        "latitude": 41.8775,
        "longitude": -87.6305,
        "maintenance_interval_days": 30,
        "last_calibration": "2024-11-15",
        "monitoring_asset": "CNC Machine #3"
    }'::jsonb
);

-- Device 8: Storage Temperature (INACTIVE)
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-008', 'acme-industrial', 'acme-hq', 'temperature', 'Tempix T100', 'INACTIVE', now() - interval '20 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-008', 'acme-industrial',
    '{
        "manufacturer": "Tempix",
        "model": "T100",
        "firmware_version": "1.9.3",
        "install_date": "2023-04-01",
        "location": "Building C - Storage",
        "latitude": 41.8790,
        "longitude": -87.6290,
        "maintenance_interval_days": 90,
        "last_calibration": "2024-01-15",
        "deactivation_reason": "Area under renovation"
    }'::jsonb
);

-- Device 9: HVAC Flow
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-009', 'acme-industrial', 'acme-hq', 'flow', 'FlowMax F200', 'ACTIVE', now() - interval '14 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-009', 'acme-industrial',
    '{
        "manufacturer": "FlowMax",
        "model": "F200",
        "firmware_version": "3.0.1",
        "install_date": "2023-10-20",
        "location": "Building A - HVAC Room",
        "latitude": 41.8784,
        "longitude": -87.6297,
        "maintenance_interval_days": 60,
        "last_calibration": "2024-08-01",
        "pipe_diameter_inches": 6
    }'::jsonb
);

-- Device 10: Tank Level
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-010', 'acme-industrial', 'acme-hq', 'level', 'TankLevel TL50', 'ACTIVE', now() - interval '10 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-010', 'acme-industrial',
    '{
        "manufacturer": "TankLevel",
        "model": "TL50",
        "firmware_version": "2.1.4",
        "install_date": "2024-03-10",
        "location": "Building B - Tank Farm",
        "latitude": 41.8772,
        "longitude": -87.6308,
        "maintenance_interval_days": 30,
        "last_calibration": "2024-12-01",
        "tank_capacity_gallons": 5000,
        "fluid_type": "Coolant"
    }'::jsonb
);

-- Device 11: New Wing Temperature (PROVISIONED - not yet active)
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-011', 'acme-industrial', 'acme-hq', 'temperature', 'Tempix T200', 'PROVISIONED', now() - interval '7 days'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-011', 'acme-industrial',
    '{
        "manufacturer": "Tempix",
        "model": "T200",
        "firmware_version": "2.4.1",
        "install_date": "2025-02-03",
        "location": "Building C - New Wing",
        "latitude": 41.8792,
        "longitude": -87.6288,
        "maintenance_interval_days": 90,
        "notes": "Pending commissioning"
    }'::jsonb
);

-- Device 12: Edge Gateway
INSERT INTO device_registry (
    device_id, tenant_id, site_id, device_type, model, status, created_at
)
VALUES (
    'SENSOR-012', 'acme-industrial', 'acme-hq', 'gateway', 'EdgeGate EG100', 'ACTIVE', now() - interval '20 months'
);

INSERT INTO device_extended_attributes (device_id, tenant_id, attributes)
VALUES (
    'SENSOR-012', 'acme-industrial',
    '{
        "manufacturer": "EdgeGate",
        "model": "EG100",
        "firmware_version": "5.2.0",
        "install_date": "2023-04-01",
        "location": "Building A - Network Closet",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "maintenance_interval_days": 180,
        "connected_sensors": 11,
        "uplink_type": "Ethernet",
        "backup_cellular": true
    }'::jsonb
);

-- ============================================
-- 5. Update Subscription Device Count
-- ============================================

UPDATE subscriptions
SET active_device_count = (
    SELECT COUNT(*) FROM device_registry
    WHERE tenant_id = 'acme-industrial' AND status = 'ACTIVE'
)
WHERE subscription_id = 'sub-acme-main-001';

-- ============================================
-- 6. Create Alert Rules
-- ============================================

INSERT INTO alert_rules (
    tenant_id, name, device_type, metric, operator, threshold, severity, enabled
)
VALUES
    ('acme-industrial', 'High Temperature Alert', 'temperature', 'temperature', '>', 30, 'WARNING', true),
    ('acme-industrial', 'Critical Temperature', 'temperature', 'temperature', '>', 40, 'CRITICAL', true),
    ('acme-industrial', 'Low Humidity Alert', 'humidity', 'humidity', '<', 30, 'WARNING', true),
    ('acme-industrial', 'High Vibration', 'vibration', 'vibration_rms', '>', 5.0, 'WARNING', true),
    ('acme-industrial', 'Tank Low Level', 'level', 'level_percent', '<', 20, 'WARNING', true),
    ('acme-industrial', 'Power Anomaly', 'power', 'power_factor', '<', 0.85, 'WARNING', true);

-- ============================================
-- 7. Verification
-- ============================================

DO $$
DECLARE
    tenant_count INT;
    site_count INT;
    device_count INT;
    active_count INT;
    rule_count INT;
BEGIN
    SELECT COUNT(*) INTO tenant_count FROM tenants WHERE tenant_id = 'acme-industrial';
    SELECT COUNT(*) INTO site_count FROM sites WHERE tenant_id = 'acme-industrial';
    SELECT COUNT(*) INTO device_count FROM device_registry WHERE tenant_id = 'acme-industrial';
    SELECT COUNT(*) INTO active_count FROM device_registry WHERE tenant_id = 'acme-industrial' AND status = 'ACTIVE';
    SELECT COUNT(*) INTO rule_count FROM alert_rules WHERE tenant_id = 'acme-industrial';

    RAISE NOTICE 'Seed complete:';
    RAISE NOTICE '  Tenants: %', tenant_count;
    RAISE NOTICE '  Sites: %', site_count;
    RAISE NOTICE '  Devices: % (% active)', device_count, active_count;
    RAISE NOTICE '  Alert Rules: %', rule_count;
END $$;

COMMIT;
```

## Run the Seed

```bash
# Apply the seed migration
docker compose exec postgres psql -U iot -d iotcloud \
  -f /path/to/052_seed_test_data.sql

# Or via docker mount:
docker compose exec -T postgres psql -U iot -d iotcloud < db/migrations/052_seed_test_data.sql
```

## Create Keycloak User for Tenant

After seeding, create a user in Keycloak for the tenant:

```bash
# Using the setup script from Phase 35
KEYCLOAK_URL=http://localhost:8080 \
KEYCLOAK_REALM=iotcloud \
KEYCLOAK_ADMIN=admin \
KEYCLOAK_ADMIN_PASSWORD=admin \
bash -c '
TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -d "username=${KEYCLOAK_ADMIN}" \
  -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r ".access_token")

# Create tenant admin user
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"acme-admin\",
    \"email\": \"admin@acme-industrial.com\",
    \"firstName\": \"Acme\",
    \"lastName\": \"Admin\",
    \"enabled\": true,
    \"emailVerified\": true,
    \"attributes\": {\"tenant_id\": [\"acme-industrial\"]},
    \"credentials\": [{
      \"type\": \"password\",
      \"value\": \"acme123\",
      \"temporary\": false
    }]
  }"

echo "Created user: acme-admin / acme123"
'
```

## Verification

```bash
# Check tenant
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT tenant_id, name, status FROM tenants;
"

# Check site
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT site_id, name, location FROM sites;
"

# Check devices
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT device_id, device_type, model, status FROM device_registry ORDER BY device_id;
"

# Check subscription
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT subscription_id, device_limit, active_device_count, status, term_end FROM subscriptions;
"

# Check alert rules
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT name, device_type, metric, operator, threshold, severity FROM alert_rules;
"

# Verify extended attributes
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT device_id, attributes->>'location' as location, attributes->>'manufacturer' as manufacturer
FROM device_extended_attributes;
"
```

## Expected Output

```
 tenant_id       |      name       | status
-----------------+-----------------+--------
 acme-industrial | Acme Industrial | ACTIVE

 site_id  | name |  location
----------+------+-------------
 acme-hq  | HQ   | Chicago, IL

 device_id   | device_type | model           | status
-------------+-------------+-----------------+------------
 SENSOR-001  | temperature | Tempix T200     | ACTIVE
 SENSOR-002  | temperature | Tempix T200     | ACTIVE
 SENSOR-003  | humidity    | HumidPro H50    | ACTIVE
 SENSOR-004  | pressure    | BaroSense P100  | ACTIVE
 SENSOR-005  | temperature | Tempix T200     | ACTIVE
 SENSOR-006  | power       | PowerMeter PM3000| ACTIVE
 SENSOR-007  | vibration   | VibeTech V400   | ACTIVE
 SENSOR-008  | temperature | Tempix T100     | INACTIVE
 SENSOR-009  | flow        | FlowMax F200    | ACTIVE
 SENSOR-010  | level       | TankLevel TL50  | ACTIVE
 SENSOR-011  | temperature | Tempix T200     | PROVISIONED
 SENSOR-012  | gateway     | EdgeGate EG100  | ACTIVE
```

## Files Created

- `db/migrations/052_seed_test_data.sql` (NEW)

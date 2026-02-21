# 007: Execute Phase 36 Cleanup

## Task

Run all Phase 36 migrations and restart services. This is a single execution script.

## Prerequisites

- Docker compose stack is running
- You have access to run docker commands

## Execution Script

Run these commands in order:

```bash
# Navigate to project root
cd /home/opsconductor/simcloud

# 1. Stop any running simulators (just in case)
docker compose --profile simulator stop 2>/dev/null || true

# 2. Check current database state
echo "=== Current database state ==="
docker compose exec -T postgres psql -U iot -d iotcloud -c "
SELECT 'activity_log' as table_name, COUNT(*) as rows FROM activity_log
UNION ALL SELECT 'device_registry', COUNT(*) FROM device_registry
UNION ALL SELECT 'tenants', COUNT(*) FROM tenants;
"

# 3. Apply cleanup migration (050)
echo ""
echo "=== Applying 050_cleanup_test_data.sql ==="
docker compose exec -T postgres psql -U iot -d iotcloud -f /docker-entrypoint-initdb.d/050_cleanup_test_data.sql

# 4. Apply retention policies (051)
echo ""
echo "=== Applying 051_log_retention_policies.sql ==="
docker compose exec -T postgres psql -U iot -d iotcloud -f /docker-entrypoint-initdb.d/051_log_retention_policies.sql

# 5. Apply fresh seed (052)
echo ""
echo "=== Applying 052_seed_test_data.sql ==="
docker compose exec -T postgres psql -U iot -d iotcloud -f /docker-entrypoint-initdb.d/052_seed_test_data.sql

# 6. Verify the seed worked
echo ""
echo "=== Verification ==="
docker compose exec -T postgres psql -U iot -d iotcloud -c "
SELECT 'tenants' as table_name, COUNT(*) as rows FROM tenants
UNION ALL SELECT 'sites', COUNT(*) FROM sites
UNION ALL SELECT 'devices', COUNT(*) FROM device_registry
UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL SELECT 'alert_rules', COUNT(*) FROM alert_rules
ORDER BY table_name;
"

# 7. Show the devices
echo ""
echo "=== Devices ==="
docker compose exec -T postgres psql -U iot -d iotcloud -c "
SELECT device_id, device_type, status FROM device_registry ORDER BY device_id;
"

# 8. Restart services to pick up rate limiting code
echo ""
echo "=== Restarting services ==="
docker compose restart ui_iot ingest_iot

# 9. Wait for services to be healthy
echo ""
echo "=== Waiting for services ==="
sleep 5

# 10. Verify services are running
docker compose ps ui_iot ingest_iot

echo ""
echo "=== Phase 36 execution complete ==="
echo "Tenant: acme-industrial"
echo "Site: acme-hq (Chicago, IL)"
echo "Devices: 12 (SENSOR-001 through SENSOR-012)"
echo "Subscription: 25 device limit, ACTIVE"
```

## Expected Output

After running, you should see:

```
=== Verification ===
 table_name    | rows
---------------+------
 alert_rules   |    6
 devices       |   12
 sites         |    1
 subscriptions |    1
 tenants       |    1

=== Devices ===
 device_id   | device_type | status
-------------+-------------+-------------
 SENSOR-001  | temperature | ACTIVE
 SENSOR-002  | temperature | ACTIVE
 SENSOR-003  | humidity    | ACTIVE
 SENSOR-004  | pressure    | ACTIVE
 SENSOR-005  | temperature | ACTIVE
 SENSOR-006  | power       | ACTIVE
 SENSOR-007  | vibration   | ACTIVE
 SENSOR-008  | temperature | INACTIVE
 SENSOR-009  | flow        | ACTIVE
 SENSOR-010  | level       | ACTIVE
 SENSOR-011  | temperature | PROVISIONED
 SENSOR-012  | gateway     | ACTIVE
```

## Troubleshooting

If migrations fail with "file not found":

```bash
# Check if migrations are mounted
docker compose exec postgres ls -la /docker-entrypoint-initdb.d/

# If not mounted, run directly:
cat db/migrations/050_cleanup_test_data.sql | docker compose exec -T postgres psql -U iot -d iotcloud
cat db/migrations/051_log_retention_policies.sql | docker compose exec -T postgres psql -U iot -d iotcloud
cat db/migrations/052_seed_test_data.sql | docker compose exec -T postgres psql -U iot -d iotcloud
```

If cleanup fails due to foreign key constraints:

```bash
# Disable FK checks temporarily
docker compose exec -T postgres psql -U iot -d iotcloud -c "SET session_replication_role = replica;"
# Then run cleanup again
```

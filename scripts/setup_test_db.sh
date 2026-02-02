#!/bin/bash
set -e

docker exec -i iot-postgres psql -U iot -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'iotcloud_test' AND pid <> pg_backend_pid();
"
docker exec -i iot-postgres psql -U iot -d postgres -c "DROP DATABASE IF EXISTS iotcloud_test;"
docker exec -i iot-postgres psql -U iot -d postgres -c "CREATE DATABASE iotcloud_test TEMPLATE iotcloud;"

echo "Test database created: iotcloud_test"

#!/bin/bash
set -e

docker exec -i iot-postgres psql -U iot -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'iotcloud_test' AND pid <> pg_backend_pid();
"
docker exec -i iot-postgres psql -U iot -d postgres -c "DROP DATABASE IF EXISTS iotcloud_test;"
docker exec -i iot-postgres psql -U iot -d postgres -c "CREATE DATABASE iotcloud_test;"

if [ -f tests/fixtures/schema_minimal.sql ]; then
    docker exec -i iot-postgres psql -U iot -d iotcloud_test < tests/fixtures/schema_minimal.sql
fi

for f in db/migrations/*.sql; do
    echo "Running migration: $f"
    docker exec -i iot-postgres psql -U iot -d iotcloud_test < "$f"
done

if [ -f tests/fixtures/test_data.sql ]; then
    docker exec -i iot-postgres psql -U iot -d iotcloud_test < tests/fixtures/test_data.sql
fi

echo "Test database created: iotcloud_test"

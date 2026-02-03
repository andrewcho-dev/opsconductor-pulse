#!/bin/bash
# Run all database migrations in order
# Usage: ./run_migrations.sh [host] [port] [database] [user]

set -e

HOST=${1:-localhost}
PORT=${2:-5432}
DATABASE=${3:-iotcloud}
USER=${4:-iot}

MIGRATIONS_DIR="$(dirname "$0")/migrations"

echo "Running migrations on $HOST:$PORT/$DATABASE as $USER"
echo "Migrations directory: $MIGRATIONS_DIR"
echo ""

# Find all .sql files and sort them
for migration in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
    filename=$(basename "$migration")
    echo "Running: $filename"
    PGPASSWORD="${PGPASSWORD:-iot_dev}" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -f "$migration" -v ON_ERROR_STOP=1
    echo "  Done: $filename"
    echo ""
done

echo "All migrations complete!"

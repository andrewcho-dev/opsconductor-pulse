#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../.."
MIGRATION_FILE="${REPO_ROOT}/db/migrations/001_webhook_delivery_v1.sql"

if [ ! -f "${MIGRATION_FILE}" ]; then
  echo "Migration not found: ${MIGRATION_FILE}" >&2
  exit 1
fi

docker exec -i iot-postgres psql -U iot -d iotcloud < "${MIGRATION_FILE}"

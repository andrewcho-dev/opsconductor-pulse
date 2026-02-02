#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../.."

DB_CONTAINER_NAME="${DB_CONTAINER_NAME:-iot-postgres}"
DB_NAME="${DB_NAME:-iotcloud}"
DB_USER="${DB_USER:-iot}"

TYPE_COL="$(
  docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -Atc \
    "SELECT column_name
     FROM information_schema.columns
     WHERE table_schema='public'
       AND table_name='fleet_alert'
       AND column_name IN ('alert_type','incident_type')
     ORDER BY CASE column_name WHEN 'alert_type' THEN 1 ELSE 2 END
     LIMIT 1;"
)"

if [ -z "${TYPE_COL}" ]; then
  echo "Could not find alert type column (expected alert_type or incident_type) on public.fleet_alert" >&2
  exit 1
fi

FINGERPRINT="demo-open-$(date +%s)-${RANDOM}"

SQL=$(cat <<EOF
INSERT INTO fleet_alert (
  tenant_id,
  site_id,
  device_id,
  ${TYPE_COL},
  fingerprint,
  status,
  severity,
  confidence,
  summary,
  details
)
VALUES (
  'enabled',
  'demo-site',
  'demo-device',
  'DEMO',
  '${FINGERPRINT}',
  'OPEN',
  3,
  0.95,
  'Demo test alert (OPEN)',
  '{"source":"insert_test_alert_open.sh"}'::jsonb
)
RETURNING id;
EOF
)

docker exec -i "${DB_CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" -c "${SQL}"

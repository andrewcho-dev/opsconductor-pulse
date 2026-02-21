# Phase 79c — Apply Missing Migrations 057–060 and 063

## Problem

`GET /api/v2/devices` returns 500 because `fetch_devices_v2` references
`dr.decommissioned_at IS NULL` which was added in migration 058.
Migrations 057, 058, 059, 060, and 063 were never applied to the running database.

## Step 1: Check which migrations exist on disk

```bash
ls db/migrations/ | sort
```

## Step 2: Check which migrations are already applied

```bash
docker compose exec db psql -U postgres -d simcloud -c "SELECT name FROM schema_migrations ORDER BY name;" 2>/dev/null \
  || docker compose exec db psql -U postgres -d simcloud -c "\dt" 2>/dev/null
```

If there is no `schema_migrations` table, migrations are applied manually. Skip to Step 3.

## Step 3: Apply missing migrations in order

Run each of these that is NOT already applied:

```bash
docker compose exec -T db psql -U postgres -d simcloud < db/migrations/057_alert_ack_fields.sql
docker compose exec -T db psql -U postgres -d simcloud < db/migrations/058_device_decommission.sql
docker compose exec -T db psql -U postgres -d simcloud < db/migrations/059_alert_escalation.sql
docker compose exec -T db psql -U postgres -d simcloud < db/migrations/060_anomaly_alert_type.sql
docker compose exec -T db psql -U postgres -d simcloud < db/migrations/063_no_telemetry_alert_type.sql
```

If a migration fails with "already exists" errors for columns or indexes, that means it was
partially applied — use IF NOT EXISTS guards or apply only the missing parts.

## Step 4: Verify decommissioned_at column exists

```bash
docker compose exec db psql -U postgres -d simcloud -c "\d device_registry" | grep decommission
```

Should show: `decommissioned_at | timestamp with time zone`

## Step 5: Verify the endpoint

```bash
curl -s -o /dev/null -w "%{http_code}" "https://192.168.10.53/api/v2/devices?limit=10&offset=0" \
  -H "Authorization: Bearer <tenant-admin-token>"
```

Should return 200.

## Step 6: Commit and push

```bash
git add -A
git commit -m "Apply missing migrations 057-060 and 063 to fix decommissioned_at 500"
git push origin main
git log --oneline -3
```

Note: If the migration SQL files themselves needed any IF NOT EXISTS fixes, commit those too.

## Report

- Output of `\d device_registry | grep decommission`
- HTTP status of /api/v2/devices after migrations
- Any migration errors encountered

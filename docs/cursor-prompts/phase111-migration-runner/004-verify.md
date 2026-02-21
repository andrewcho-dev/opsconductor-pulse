# Phase 111 — Verify Migration Runner

## Step 1: Build migrator image

```bash
cd compose && docker compose build migrator
```

Expected: builds successfully.

## Step 2: Run migrator against existing DB

```bash
cd compose && docker compose run --rm migrator
```

Expected output (all migrations already applied — skipped):
```json
{"msg": "Starting migration runner"}
{"msg": "Skipping 001_*.sql — already applied"}
...
{"msg": "Migration complete. 0 migration(s) applied."}
```

## Step 3: schema_migrations table populated

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT version, filename, applied_at FROM schema_migrations ORDER BY version LIMIT 10;"
```

Expected: rows for every migration that was previously applied manually.

**If the table is empty** (fresh tracking table), the migrator will apply
all migrations in order. This is correct — it means prior manual applies
are not tracked, but idempotent SQL (`CREATE TABLE IF NOT EXISTS`,
`ADD COLUMN IF NOT EXISTS`) will skip silently.

## Step 4: Idempotency — run migrator a second time

```bash
cd compose && docker compose run --rm migrator
```

Expected: all migrations skipped, exit 0. No errors, no duplicate applies.

## Step 5: Full stack restart

Bring the entire stack down and back up. The migrator should run before
any application service starts:

```bash
cd compose
docker compose down
docker compose up -d
docker logs iot-migrator --follow &   # watch migrator logs
sleep 30
docker compose ps
```

Expected:
- `iot-migrator` exits with code 0 before `iot-ingest` starts
- All application containers reach `healthy` or `running` state
- No `relation does not exist` errors in any service logs

## Step 6: Verify ingest starts without init_db errors

```bash
docker logs iot-ingest --tail=30 | grep -i "error\|init_db\|CREATE TABLE"
```

Expected: no schema creation logs, no errors.

## Step 7: Commit

```bash
git add \
  db/migrate.py \
  db/Dockerfile.migrator \
  db/run_migrations.sh \
  compose/docker-compose.yml \
  services/ingest_iot/ingest.py

git commit -m "feat: versioned migration runner — replaces inline init_db()

- db/migrate.py: migration runner with schema_migrations tracking table,
  ordered apply, skip-if-applied, exits non-zero on failure
- db/Dockerfile.migrator: minimal python:3.11-slim image with psycopg2-binary
- docker-compose.yml: migrator service runs before all app containers
  (service_completed_successfully); added missing health checks for ui, api,
  ops_worker; pinned all image tags to specific versions
- ingest.py: removed init_db() — migrator now owns schema bootstrap
- db/run_migrations.sh: marked deprecated, kept for emergency manual use"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `db/migrate.py` exists and runs cleanly
- [ ] `schema_migrations` table populated in Postgres
- [ ] Running migrator twice is idempotent (second run skips all)
- [ ] Full `docker compose down && up` applies migrator before app services
- [ ] `iot-ingest` starts without `init_db()` or schema creation
- [ ] All image tags pinned (no `latest`)
- [ ] Missing health checks added for ui, api, ops_worker

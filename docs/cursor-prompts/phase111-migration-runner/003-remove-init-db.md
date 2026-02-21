# Phase 111 — Remove init_db() from ingest.py

## Context

`services/ingest_iot/ingest.py` currently calls `init_db()` at startup which
runs `CREATE TABLE IF NOT EXISTS` DDL. Now that the migrator owns the schema,
this is redundant and potentially dangerous (it could silently create tables
that should have been created by a migration, masking migration failures).

## Step 1: Find init_db()

```bash
grep -n "init_db\|CREATE TABLE\|CREATE EXTENSION\|CREATE INDEX" \
  services/ingest_iot/ingest.py | head -30
```

## Step 2: Evaluate what init_db() creates

Read the `init_db()` function body. Check each `CREATE TABLE IF NOT EXISTS`
statement against the migration files:

```bash
for table in $(grep "CREATE TABLE IF NOT EXISTS" services/ingest_iot/ingest.py \
  | grep -oP '(?<=EXISTS )[\w]+'); do
  echo "Table: $table"
  grep -l "$table" db/migrations/*.sql | head -3
done
```

Every table that `init_db()` creates should already exist in a migration file.
If any table created by `init_db()` is NOT in a migration file, create a
migration for it before removing `init_db()`.

## Step 3: Remove or stub init_db()

Once confirmed that all tables are covered by migrations, remove `init_db()`
and its call site:

```python
# Remove the entire init_db() method/function
# Remove the call: await self.init_db() or init_db()
```

If `init_db()` is a method on a class (e.g. `IngestService`), delete the
entire method. If it's called in `main()` or `startup()`, remove that call.

## Step 4: Remove CREATE EXTENSION calls if present

`CREATE EXTENSION IF NOT EXISTS timescaledb` and similar should be in
migrations. Check:

```bash
grep -n "CREATE EXTENSION" db/migrations/*.sql | head -5
```

If `CREATE EXTENSION` is already in an early migration (e.g. `001_*.sql`),
it does not need to stay in `ingest.py`.

## Step 5: Verify ingest still starts after removing init_db()

```bash
docker compose -f compose/docker-compose.yml up -d --build ingest
sleep 5
docker logs iot-ingest --tail=20
```

Expected: ingest starts cleanly without schema errors. The migrator has
already created all tables, so ingest doesn't need to create anything.

## Step 6: Verify existing run_migrations.sh is superseded

The `db/run_migrations.sh` script was used for manual migration runs.
It is now superseded by the migrator container. Add a comment to the top:

```bash
#!/bin/bash
# DEPRECATED: Use the migrator container (docker compose up migrator) instead.
# This script is kept for emergency manual use only.
```

Do not delete it — it's useful as a fallback for manual intervention.

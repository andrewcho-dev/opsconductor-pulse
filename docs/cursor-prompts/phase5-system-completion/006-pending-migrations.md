# Task 006: Run Pending Migrations

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Migration `012_delivery_log.sql` was created in Phase 4 but needs to be run. Additionally, we should verify all migrations have been applied and create a migration runner script for easier deployment.

**Read first**:
- `db/migrations/` (all migration files)
- `db/migrations/012_delivery_log.sql` (pending migration)

**Depends on**: None

---

## Task

### 6.1 Review 012_delivery_log.sql

Verify the migration file exists and is correct:

```sql
-- db/migrations/012_delivery_log.sql
CREATE TABLE IF NOT EXISTS delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(64) NOT NULL,
    integration_id UUID NOT NULL,
    integration_name VARCHAR(128),
    delivery_type VARCHAR(16) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL,
    error TEXT,
    duration_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_delivery_log_alert_id ON delivery_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_tenant_id ON delivery_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_created_at ON delivery_log(created_at);

ALTER TABLE delivery_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS delivery_log_tenant_policy ON delivery_log
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT ON delivery_log TO pulse_app;
GRANT SELECT ON delivery_log TO pulse_operator;
```

### 6.2 Create migration runner script

Create `db/run_migrations.sh`:

```bash
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
```

### 6.3 Create migration verification query

Create `db/verify_migrations.sql`:

```sql
-- Verify all expected tables exist
SELECT 'integrations' AS table_name, EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'integrations') AS exists
UNION ALL
SELECT 'integration_routes', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'integration_routes')
UNION ALL
SELECT 'delivery_jobs', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'delivery_jobs')
UNION ALL
SELECT 'delivery_attempts', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'delivery_attempts')
UNION ALL
SELECT 'delivery_log', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'delivery_log')
UNION ALL
SELECT 'operator_audit_log', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'operator_audit_log')
UNION ALL
SELECT 'rate_limits', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rate_limits');

-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('integrations', 'integration_routes', 'delivery_jobs', 'delivery_attempts', 'delivery_log', 'device_state', 'fleet_alert');

-- Verify SNMP columns exist on integrations
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'integrations'
  AND column_name IN ('type', 'snmp_host', 'snmp_port', 'snmp_config', 'snmp_oid_prefix');
```

### 6.4 Update docker-compose to run migrations on startup

This is optional but useful. Add a migration service to `compose/docker-compose.yml` (or document manual process):

Add to documentation in `db/README.md`:

```markdown
# Database Migrations

## Running Migrations

### Manual (recommended for production)

```bash
cd db
PGPASSWORD=iot_dev ./run_migrations.sh localhost 5432 iotcloud iot
```

### Individual Migration

```bash
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/012_delivery_log.sql
```

## Verifying Migrations

```bash
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/verify_migrations.sql
```

## Migration Files

| # | File | Description |
|---|------|-------------|
| 001 | webhook_delivery_v1.sql | Core delivery tables |
| 002 | operator_audit_log.sql | Operator audit logging |
| 003 | rate_limits.sql | Rate limiting table |
| 004 | enable_rls.sql | Enable RLS on tables |
| 005 | audit_rls_bypass.sql | Operator RLS bypass |
| 011 | snmp_integrations.sql | SNMP support columns |
| 012 | delivery_log.sql | Delivery logging table |

## Notes

- Migrations are idempotent (use IF NOT EXISTS)
- Run in numeric order
- Gap in numbering (006-010) reserved for future use
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| VERIFY | `db/migrations/012_delivery_log.sql` |
| CREATE | `db/run_migrations.sh` |
| CREATE | `db/verify_migrations.sql` |
| CREATE | `db/README.md` |

---

## Acceptance Criteria

- [ ] Migration 012 exists and is valid SQL
- [ ] run_migrations.sh script created and executable
- [ ] verify_migrations.sql queries work
- [ ] db/README.md documents migration process
- [ ] All migrations run without error on fresh database

**Test**:
```bash
# Make script executable
chmod +x db/run_migrations.sh

# Run all migrations
cd db && PGPASSWORD=iot_dev ./run_migrations.sh localhost 5432 iotcloud iot

# Verify
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/verify_migrations.sql
```

---

## Commit

```
Add migration tooling and verify all migrations

- Create run_migrations.sh script
- Create verify_migrations.sql verification queries
- Add db/README.md documentation
- Verify migration 012 (delivery_log) exists

Part of Phase 5: System Completion
```

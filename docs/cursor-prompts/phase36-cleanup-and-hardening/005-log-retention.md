# 005: Automatic Log Retention Policies

## Task

Implement automatic log cleanup policies to prevent unbounded log growth.

## Retention Policies

| Table | Retention | Reasoning |
|-------|-----------|-----------|
| `activity_log` | 7 days | High volume, debugging only |
| `device_telemetry` | 90 days (or per subscription) | Core data, tiered retention |
| `device_state` | 30 days | Snapshot history |
| `fleet_alert` | 90 days | Incident history |
| `operator_audit_log` | 1 year | Compliance |
| `subscription_audit` | 2 years | Financial compliance |

## Implementation

### 1. TimescaleDB Retention Policies

TimescaleDB has built-in retention policy support via `add_retention_policy`.

**File:** `db/migrations/051_log_retention_policies.sql`

```sql
-- ============================================
-- Migration: 051_log_retention_policies.sql
-- Purpose: Add automatic retention policies for logs
-- ============================================

BEGIN;

-- ============================================
-- 1. Activity Log (7 days)
-- ============================================

-- First, ensure it's a hypertable (if not already)
DO $$
BEGIN
    -- Check if already a hypertable
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'activity_log'
    ) THEN
        -- Convert to hypertable
        PERFORM create_hypertable(
            'activity_log',
            'created_at',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
        RAISE NOTICE 'Converted activity_log to hypertable';
    END IF;
END $$;

-- Add retention policy
SELECT add_retention_policy(
    'activity_log',
    drop_after => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- 2. Device Telemetry (90 days default)
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'device_telemetry'
    ) THEN
        PERFORM create_hypertable(
            'device_telemetry',
            'timestamp',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    END IF;
END $$;

SELECT add_retention_policy(
    'device_telemetry',
    drop_after => INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ============================================
-- 3. Device State (30 days)
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'device_state'
    ) THEN
        PERFORM create_hypertable(
            'device_state',
            'state_time',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    END IF;
END $$;

SELECT add_retention_policy(
    'device_state',
    drop_after => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ============================================
-- 4. Fleet Alert (90 days)
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'fleet_alert'
    ) THEN
        PERFORM create_hypertable(
            'fleet_alert',
            'triggered_at',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    END IF;
END $$;

SELECT add_retention_policy(
    'fleet_alert',
    drop_after => INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ============================================
-- 5. Verify Policies
-- ============================================

-- View all retention policies
SELECT * FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention';

COMMIT;
```

### 2. Manual Cleanup for Non-Hypertables

For tables that aren't hypertables (or can't be), use scheduled cleanup.

**File:** `services/maintenance/log_cleanup.py` (NEW)

```python
"""
Scheduled log cleanup for non-hypertable tables.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict

import asyncpg

logger = logging.getLogger(__name__)

# Retention policies (days)
RETENTION_POLICIES: Dict[str, int] = {
    'operator_audit_log': 365,      # 1 year
    'subscription_audit': 730,       # 2 years
    'subscription_notifications': 90,
}


async def cleanup_table(
    conn: asyncpg.Connection,
    table_name: str,
    timestamp_column: str,
    retention_days: int,
) -> int:
    """
    Delete old rows from a table.
    Returns number of rows deleted.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    # Delete in batches to avoid long locks
    total_deleted = 0
    batch_size = 10000

    while True:
        result = await conn.execute(f"""
            DELETE FROM {table_name}
            WHERE ctid IN (
                SELECT ctid FROM {table_name}
                WHERE {timestamp_column} < $1
                LIMIT $2
            )
        """, cutoff, batch_size)

        # Parse "DELETE X" result
        deleted = int(result.split()[-1])
        total_deleted += deleted

        if deleted < batch_size:
            break

        # Brief pause to reduce lock contention
        await asyncio.sleep(0.1)

    return total_deleted


async def run_cleanup(database_url: str):
    """Run cleanup for all configured tables."""
    conn = await asyncpg.connect(database_url)

    try:
        logger.info("Starting log cleanup...")

        for table_name, retention_days in RETENTION_POLICIES.items():
            try:
                # Determine timestamp column
                timestamp_col = 'created_at'
                if table_name == 'subscription_notifications':
                    timestamp_col = 'scheduled_at'

                deleted = await cleanup_table(
                    conn, table_name, timestamp_col, retention_days
                )

                if deleted > 0:
                    logger.info(f"Cleaned {table_name}: {deleted} rows deleted (retention: {retention_days} days)")
                else:
                    logger.debug(f"No old rows in {table_name}")

            except Exception as e:
                logger.error(f"Failed to clean {table_name}: {e}")

        # Vacuum to reclaim space
        logger.info("Running VACUUM ANALYZE...")
        await conn.execute("VACUUM ANALYZE")

        logger.info("Log cleanup complete")

    finally:
        await conn.close()


async def main():
    import os
    database_url = os.getenv('DATABASE_URL', 'postgresql://iot:iot@localhost:5432/iotcloud')
    await run_cleanup(database_url)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### 3. Scheduled Job (Cron or Systemd Timer)

**File:** `scripts/cron/log-cleanup.sh`

```bash
#!/bin/bash
set -e

cd /app  # or your application directory

# Run the cleanup script
python -m services.maintenance.log_cleanup

# Or via docker:
# docker compose exec -T maintenance python -m services.maintenance.log_cleanup
```

**Crontab entry:**

```cron
# Run log cleanup daily at 3 AM
0 3 * * * /app/scripts/cron/log-cleanup.sh >> /var/log/log-cleanup.log 2>&1
```

**Or systemd timer:**

**File:** `/etc/systemd/system/iot-log-cleanup.service`

```ini
[Unit]
Description=IoT Platform Log Cleanup
After=postgresql.service

[Service]
Type=oneshot
User=iot
WorkingDirectory=/app
ExecStart=/usr/bin/python -m services.maintenance.log_cleanup
Environment=DATABASE_URL=postgresql://iot:iot@localhost:5432/iotcloud
```

**File:** `/etc/systemd/system/iot-log-cleanup.timer`

```ini
[Unit]
Description=Run IoT log cleanup daily

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable timer
sudo systemctl daemon-reload
sudo systemctl enable iot-log-cleanup.timer
sudo systemctl start iot-log-cleanup.timer
```

### 4. Docker Compose Integration

**File:** `docker-compose.yml`

Add a maintenance service:

```yaml
services:
  # ... other services ...

  maintenance:
    build: ./services/maintenance
    environment:
      - DATABASE_URL=postgresql://iot:iot@postgres:5432/iotcloud
    depends_on:
      - postgres
    # Run as cron-like scheduler
    command: >
      sh -c "
        while true; do
          python -m log_cleanup
          sleep 86400  # Run daily
        done
      "
    restart: unless-stopped
```

Or use a proper scheduler like `supercronic`:

**File:** `services/maintenance/Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN pip install asyncpg

# Install supercronic for cron-like scheduling
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 \
    -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic

WORKDIR /app
COPY . .

# Crontab file
COPY crontab /etc/crontab

CMD ["supercronic", "/etc/crontab"]
```

**File:** `services/maintenance/crontab`

```cron
# Run log cleanup daily at 3 AM UTC
0 3 * * * python -m log_cleanup
```

### 5. Monitoring Retention Jobs

**File:** `db/migrations/051_log_retention_policies.sql` (append)

```sql
-- Create a table to track cleanup runs
CREATE TABLE IF NOT EXISTS maintenance_log (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    rows_affected BIGINT,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    error_message TEXT,
    details JSONB
);

CREATE INDEX idx_maintenance_log_job ON maintenance_log(job_name, started_at DESC);

-- View TimescaleDB job history
CREATE OR REPLACE VIEW retention_job_history AS
SELECT
    job_id,
    hypertable_name,
    total_runs,
    total_successes,
    total_failures,
    last_run_status,
    last_run_started_at,
    last_run_duration,
    next_scheduled_run
FROM timescaledb_information.job_stats
WHERE proc_name = 'policy_retention';
```

Update cleanup script to log its runs:

```python
async def run_cleanup(database_url: str):
    conn = await asyncpg.connect(database_url)

    try:
        # Log start
        job_id = await conn.fetchval("""
            INSERT INTO maintenance_log (job_name, started_at, status)
            VALUES ('log_cleanup', now(), 'RUNNING')
            RETURNING id
        """)

        total_deleted = 0
        details = {}

        for table_name, retention_days in RETENTION_POLICIES.items():
            try:
                deleted = await cleanup_table(conn, table_name, 'created_at', retention_days)
                total_deleted += deleted
                details[table_name] = deleted
            except Exception as e:
                details[table_name] = f"ERROR: {e}"

        # Log completion
        await conn.execute("""
            UPDATE maintenance_log
            SET completed_at = now(),
                status = 'COMPLETED',
                rows_affected = $2,
                details = $3
            WHERE id = $1
        """, job_id, total_deleted, json.dumps(details))

    except Exception as e:
        # Log error
        await conn.execute("""
            UPDATE maintenance_log
            SET completed_at = now(),
                status = 'FAILED',
                error_message = $2
            WHERE id = $1
        """, job_id, str(e))
        raise

    finally:
        await conn.close()
```

## Verification

```bash
# Check TimescaleDB retention policies
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT * FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention';
"

# Check job history
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT * FROM retention_job_history;
"

# Manually trigger retention (for testing)
docker compose exec postgres psql -U iot -d iotcloud -c "
CALL run_job(1001);  -- Replace with actual job_id
"

# Check maintenance log
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT * FROM maintenance_log ORDER BY started_at DESC LIMIT 10;
"

# Check table sizes after cleanup
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
"
```

## Files Created/Modified

- `db/migrations/051_log_retention_policies.sql` (NEW)
- `services/maintenance/log_cleanup.py` (NEW)
- `services/maintenance/Dockerfile` (NEW)
- `services/maintenance/crontab` (NEW)
- `docker-compose.yml` (MODIFIED - add maintenance service)

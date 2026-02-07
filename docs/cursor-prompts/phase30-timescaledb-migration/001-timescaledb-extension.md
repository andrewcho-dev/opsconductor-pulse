# Phase 30.1: Enable TimescaleDB Extension

## Task

Switch to TimescaleDB-enabled PostgreSQL image and enable the extension.

---

## Update Docker Compose

**File:** `compose/docker-compose.yml`

Change the postgres service to use TimescaleDB image:

```yaml
  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: iot-postgres
    environment:
      POSTGRES_DB: iotcloud
      POSTGRES_USER: iot
      POSTGRES_PASSWORD: iot_dev
    ports:
      - "5432:5432"
    volumes:
      - ../data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U iot -d iotcloud -h 127.0.0.1 -p 5432"]
      interval: 2s
      timeout: 3s
      retries: 30
      start_period: 5s
    restart: unless-stopped
```

Note: `timescale/timescaledb:latest-pg16` includes PostgreSQL 16 + TimescaleDB extension.

---

## Create Extension Migration

**File:** `db/migrations/020_enable_timescaledb.sql`

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Verify installation
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        RAISE EXCEPTION 'TimescaleDB extension not installed';
    END IF;
    RAISE NOTICE 'TimescaleDB version: %', (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb');
END $$;
```

---

## Recreate PostgreSQL Container

Since we're changing the base image, we need to be careful with existing data.

**Option A: Fresh start (dev environment)**
```bash
cd /home/opsconductor/simcloud/compose

# Stop all services
docker compose down

# Remove postgres volume (WARNING: destroys data)
docker volume rm compose_postgres_data 2>/dev/null || true
rm -rf ../data/postgres

# Start with new image
docker compose up -d postgres

# Wait for healthy
docker compose exec postgres pg_isready -U iot -d iotcloud

# Run migrations (including new timescaledb one)
docker compose exec postgres psql -U iot -d iotcloud -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
```

**Option B: Preserve data (production)**
```bash
# Backup first
docker compose exec postgres pg_dump -U iot iotcloud > backup_before_timescale.sql

# Stop postgres
docker compose stop postgres

# Update docker-compose.yml with new image
# ... edit file ...

# Start with new image (data preserved)
docker compose up -d postgres

# Enable extension
docker compose exec postgres psql -U iot -d iotcloud -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
```

---

## Verification

```bash
# Check TimescaleDB is enabled
docker compose exec postgres psql -U iot -d iotcloud -c "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';"

# Should output something like:
#  extversion
# ------------
#  2.14.2

# Check TimescaleDB functions are available
docker compose exec postgres psql -U iot -d iotcloud -c "\df create_hypertable"
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `compose/docker-compose.yml` |
| CREATE | `db/migrations/020_enable_timescaledb.sql` |

# Phase 113 — Dedicated Keycloak Database

## Context

Keycloak currently uses the same `iotcloud` database as the application.
This means Keycloak tables (prefixed `kc_*`) sit alongside application tables.
For production these must be separated: Keycloak gets its own database and
its own database user.

## Step 1: Create keycloak DB and user

Add a migration or a one-time init script. The cleanest approach is to add
this to the Postgres init, but since we now have a migration runner, add it
as a standalone SQL script that runs before Keycloak starts.

Create `db/keycloak_db_init.sql`:

```sql
-- Create dedicated Keycloak database and user
-- Run once against Postgres as superuser (iot user has CREATEDB privilege)

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') THEN
    CREATE USER keycloak WITH PASSWORD 'PLACEHOLDER';
  END IF;
END $$;

-- Ensure password is up to date (safe to re-run)
ALTER USER keycloak WITH PASSWORD 'PLACEHOLDER';

CREATE DATABASE keycloak_db
  WITH OWNER = keycloak
  ENCODING = 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8'
  TEMPLATE = template0;

GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak;
```

**Note:** The `PLACEHOLDER` password must be replaced at runtime.
Add to `compose/.env` and `.env.example`:
```bash
# In .env
KC_DB_USER_PASSWORD=CHANGE_ME_strong_password_here

# In .env.example
KC_DB_USER_PASSWORD=CHANGE_ME_generate_with_secrets_token_hex
```

## Step 2: Run keycloak DB init

Add a `keycloak-db-init` service in docker-compose.yml that runs once
after Postgres is healthy and before Keycloak starts:

```yaml
  keycloak-db-init:
    image: timescale/timescaledb:2.16.1-pg16
    container_name: iot-keycloak-db-init
    environment:
      PGPASSWORD: ${POSTGRES_PASSWORD}
    command: >
      bash -c "
        PGPASSWORD=$$POSTGRES_PASSWORD psql -h iot-postgres -U iot -d postgres
        -c \"DO \\$\\$ BEGIN IF NOT EXISTS
        (SELECT FROM pg_roles WHERE rolname = 'keycloak')
        THEN CREATE USER keycloak WITH PASSWORD '${KC_DB_USER_PASSWORD}'; END IF; END \\$\\$;\"
        -c \"ALTER USER keycloak WITH PASSWORD '${KC_DB_USER_PASSWORD}';\"
        -c \"SELECT 'CREATE DATABASE keycloak_db OWNER keycloak'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\\gexec\"
        -c \"GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak;\"
      "
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"
    networks:
      - iot-network
```

**Simpler alternative** — add the keycloak DB creation to the Postgres
entrypoint. Create `compose/postgres/init-keycloak-db.sh`:

```bash
#!/bin/bash
# Runs once when Postgres container initialises for the first time.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') THEN
      CREATE USER keycloak WITH PASSWORD '${KC_DB_USER_PASSWORD}';
    END IF;
  END \$\$;

  ALTER USER keycloak WITH PASSWORD '${KC_DB_USER_PASSWORD}';

  SELECT 'CREATE DATABASE keycloak_db OWNER keycloak'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\gexec

  GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak;
EOSQL
```

Mount it in docker-compose.yml:
```yaml
  postgres:
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./postgres/init-keycloak-db.sh:/docker-entrypoint-initdb.d/init-keycloak-db.sh:ro
    environment:
      KC_DB_USER_PASSWORD: ${KC_DB_USER_PASSWORD}
```

**Use whichever approach is simpler** for the current Postgres setup.
The init-script approach runs only on first DB initialisation; the
`keycloak-db-init` service approach runs on every stack start (but is idempotent).

## Step 3: Update Keycloak DB connection in docker-compose.yml

```yaml
  keycloak:
    environment:
      KC_DB: postgres
      KC_DB_URL: "jdbc:postgresql://iot-postgres:5432/keycloak_db"
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KC_DB_USER_PASSWORD}
```

Remove the old `KC_DB_PASSWORD: ${KC_DB_PASSWORD}` (which used the app DB password).

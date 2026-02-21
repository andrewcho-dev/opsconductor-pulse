# Prompt 001 — Add PgBouncer to docker-compose

Read `docker-compose.yml` fully.

## Add pgbouncer service

Add after the `db` service:

```yaml
pgbouncer:
  image: edoburu/pgbouncer:1.22.1
  environment:
    DATABASE_URL: "postgres://pulse_app:${POSTGRES_APP_PASSWORD}@db:5432/pulse"
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 200
    DEFAULT_POOL_SIZE: 20
    MIN_POOL_SIZE: 5
    RESERVE_POOL_SIZE: 5
    RESERVE_POOL_TIMEOUT: 3
    SERVER_RESET_QUERY: DISCARD ALL
    LOG_CONNECTIONS: 0
    LOG_DISCONNECTIONS: 0
    AUTH_TYPE: scram-sha-256
  ports:
    - "6432:5432"
  depends_on:
    db:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "pg_isready", "-h", "localhost", "-p", "5432"]
    interval: 10s
    timeout: 5s
    retries: 3
```

## Environment Variable

Add to `.env.example` (not `.env`):
```
PGBOUNCER_HOST=pgbouncer
PGBOUNCER_PORT=6432
```

## Note on LISTEN/NOTIFY

PgBouncer in transaction mode does NOT support LISTEN/NOTIFY. Services that use
LISTEN must connect **directly to the `db` service** for their notification connection.
This is handled in prompt 003.

## Acceptance Criteria

- [ ] `pgbouncer` service added to docker-compose.yml
- [ ] Uses `edoburu/pgbouncer:1.22.1`
- [ ] POOL_MODE=transaction
- [ ] Depends on db with health check
- [ ] `PGBOUNCER_HOST` / `PGBOUNCER_PORT` in .env.example

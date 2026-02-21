# Prompt 005 — Add `ops_worker` to `docker-compose.yml`

## Context

The `ops_worker` service exists as code. This prompt wires it into the compose stack so it runs alongside the other services.

## Your Task

### Step 1: Read `docker-compose.yml` fully

Understand:
- How other worker services are defined (e.g., `dispatcher`, `delivery_worker`, `evaluator_iot`)
- What environment variables they receive (DB connection string, service URLs)
- What `depends_on` relationships exist
- What networks they join

### Step 2: Add the `ops_worker` service definition

Follow the exact pattern of an existing worker service (e.g., `dispatcher`). The new entry needs:

```yaml
ops_worker:
  build:
    context: ./services/ops_worker
  environment:
    - DATABASE_URL=${DATABASE_URL}
    # Add all env vars from services/ops_worker/.env.example
    # Include URLs for all services the health monitor pings
  depends_on:
    - db
    # Add any other services ops_worker needs to be ready
  networks:
    - [same networks as other workers]
  restart: unless-stopped
```

### Step 3: Service endpoint URLs for health monitor

The health monitor pings the other services' health endpoints. These need to be passed as env vars. Look at what services are defined in docker-compose.yml and what health endpoints they expose (e.g., `http://evaluator_iot:8001/health`). Add each one as an env var in ops_worker's environment section.

### Step 4: Confirm no duplicate work

Verify that the old health monitor and metrics collector tasks are gone from `ui_iot` (prompt 004 done). There must be exactly ONE process running each task — if both ui_iot and ops_worker run the health monitor simultaneously, you will get duplicate rows in the service_health table.

### Step 5: Test the compose stack

```bash
docker compose build ops_worker
docker compose up ops_worker -d
docker compose logs ops_worker --tail=20
```

Confirm:
- Service starts without errors
- Health monitor writes appear in the DB after 60s
- Metrics collector writes appear in the DB after 5s

## Acceptance Criteria

- [ ] `ops_worker` is defined in `docker-compose.yml` following existing worker patterns
- [ ] All required env vars from `.env.example` are present in the compose definition
- [ ] `docker compose build ops_worker` succeeds
- [ ] `docker compose logs ops_worker` shows the loops running without errors
- [ ] No duplicate health monitor or metrics collector running in ui_iot

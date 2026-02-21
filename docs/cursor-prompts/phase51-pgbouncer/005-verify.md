# Prompt 005 — Verify Phase 51

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: Docker Compose Lint

```bash
docker compose config --quiet 2>&1
```

Should output no errors.

## Step 3: Checklist

- [ ] `pgbouncer` service in docker-compose.yml
- [ ] POOL_MODE=transaction
- [ ] Services use reduced pool sizes (min=2, max=10)
- [ ] `NOTIFY_DATABASE_URL` documented in evaluator/dispatcher/delivery_worker .env.example
- [ ] evaluator/dispatcher/delivery_worker use dedicated notify_conn for LISTEN
- [ ] `SET LOCAL ROLE` (not `SET ROLE`) confirmed in ingest_iot
- [ ] 4 unit tests pass in test_pgbouncer_bypass.py

## Report

Output PASS / FAIL per criterion.

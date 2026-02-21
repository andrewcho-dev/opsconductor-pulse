# Phase 110 — Verify Secrets Cleanup

## Step 1: No secrets in tracked files

```bash
# Search for known secret patterns in tracked files
git grep -n "iot_dev\|change-me-now\|admin_dev\|192\.168\." -- \
  '*.yml' '*.yaml' '*.py' '*.json' '*.conf' | grep -v ".env.example"
```

Expected: zero results (or only `.env.example` with `CHANGE_ME_` placeholders).

```bash
# Confirm .env is not tracked
git ls-files compose/.env
```

Expected: no output.

## Step 2: docker compose config validates cleanly

```bash
cd compose && docker compose config > /dev/null && echo "OK"
```

Expected: `OK` with no warnings about unset variables.

## Step 3: Services start with new env vars

```bash
cd compose && docker compose up -d --no-build 2>&1 | tail -10
sleep 5
docker compose ps
```

Expected: all services `Up` or `healthy`. If any fail due to a missing env
var, add it to `.env` and re-run.

## Step 4: Spot-check a running service reads the env var

```bash
docker exec iot-ui env | grep PG_PASS
```

Expected: `PG_PASS=iot_dev_local` (or whatever is in `.env`) — NOT `iot_dev`.

## Step 5: Commit

```bash
# Stage only tracked files (not .env)
git add \
  compose/.env.example \
  compose/docker-compose.yml \
  services/maintenance/log_cleanup.py \
  services/subscription_worker/worker.py \
  .gitignore

# If deleting legacy Dockerfiles:
git rm services/ingest/Dockerfile \
       services/evaluator/Dockerfile \
       simulator/device_sim/Dockerfile 2>/dev/null || true

git commit -m "chore: extract secrets from repo — .env.example, parameterise compose

- compose/.env.example: documents all required env vars with CHANGE_ME_ placeholders
- compose/.env: replaced real LAN IP (192.168.10.53) with localhost defaults;
  removed from git tracking
- docker-compose.yml: all hardcoded passwords, keys, and IPs replaced with
  \${VAR} references — no hardcoded fallbacks for any secret
- maintenance/log_cleanup.py: remove hardcoded DB URL fallback; use shared JSON logger
- subscription_worker: fix PgBouncer hostname; use shared JSON logger
- Removed orphaned legacy Dockerfiles (services/ingest/, services/evaluator/, simulator/device_sim/)
- .gitignore: add compose/.env"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `git grep "iot_dev"` returns zero results in tracked files
- [ ] `git grep "change-me-now"` returns zero results in tracked files
- [ ] `git grep "192\.168"` returns zero results in tracked files
- [ ] `compose/.env` is not tracked by git (`git ls-files compose/.env` = empty)
- [ ] `compose/.env.example` is committed with `CHANGE_ME_` placeholders
- [ ] `docker compose config` validates with no errors
- [ ] All services start successfully with new `.env`

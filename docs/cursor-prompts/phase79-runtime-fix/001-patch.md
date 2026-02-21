# Phase 79b — Patch: pool NameError + pgbouncer image tag

## Fix 1: pool NameError in list_subscriptions

Read `services/ui_iot/routes/customer.py` and find the `list_subscriptions` function.

The function uses `pool` but it is not injected as a dependency. Compare the signature to working endpoints like `list_devices` or `list_alerts` in the same file to see the correct pattern.

The fix is to add `pool=Depends(get_db_pool)` to the function signature, matching every other endpoint in the file.

Do NOT rewrite the function body — only fix the signature.

Verify the fix:
```bash
docker compose restart ui_iot
curl -s -o /dev/null -w "%{http_code}" http://localhost/customer/subscriptions -H "Authorization: Bearer <tenant-admin-token>"
```
Should return 200.

## Fix 2: pgbouncer image tag in docker-compose

Read `docker-compose.yml` (or `docker-compose.yaml`) and find the pgbouncer service image line.

Change:
```
image: edoburu/pgbouncer:1.22.1
```
To:
```
image: edoburu/pgbouncer:latest
```

This makes the compose file pullable again. Document in a comment that 1.22.1 was removed from Docker Hub.

## Fix 3: Commit and push

```bash
git add -A
git commit -m "Fix pool NameError in list_subscriptions and update pgbouncer image tag to latest

- customer.py: add pool=Depends(get_db_pool) to list_subscriptions signature
- docker-compose: update edoburu/pgbouncer from 1.22.1 (removed from Hub) to latest"
git push origin main
git log --oneline -5
```

## Report

- HTTP status of /customer/subscriptions after restart
- Confirm pgbouncer image line updated in compose file
- git log output

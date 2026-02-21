# Phase 103 — Verify Keycloak Resilience

## Step 1: Normal auth still works

```bash
# Get a token (adjust realm/client/user/pass to match dev setup)
TOKEN=$(curl -s -X POST \
  "http://localhost:8080/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=admin&password=admin" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices | python3 -m json.tool | head -10
```

Expected: 200 OK with device list.

## Step 2: JWKS cache is populated at startup

```bash
docker logs iot-ui 2>&1 | grep jwks_refreshed | tail -3
```

Expected: `{"msg": "jwks_refreshed", "key_count": 1, ...}`

## Step 3: Simulate Keycloak outage

```bash
# Stop keycloak
docker compose -f compose/docker-compose.yml stop keycloak
sleep 2

# Auth should still work from cache
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices | python3 -m json.tool | head -5
```

Expected: 200 OK — cache still serves valid keys.

```bash
# Check logs — expect stale-cache warning on next TTL expiry, not 503
docker logs iot-ui --tail=5 2>&1 | grep -E "jwks|stale"
```

## Step 4: Restart Keycloak

```bash
docker compose -f compose/docker-compose.yml start keycloak
sleep 5

# Confirm cache refreshes
docker logs iot-ui --tail=5 2>&1 | grep jwks_refreshed
```

## Step 5: Commit

```bash
git add \
  services/shared/jwks_cache.py \
  services/ui_iot/auth.py \
  services/ui_iot/app.py \
  compose/docker-compose.yml

git commit -m "feat: JWKS cache with TTL and stale-on-error fallback

- shared/jwks_cache.py: in-memory JWKS cache, 10min TTL, 1hr stale limit,
  5min background refresh, structured log on each fetch
- auth.py: replaces direct JWKS fetch with JwksCache.get()
- app.py: start/stop cache in lifespan hooks
- Keycloak outage no longer drops authenticated requests within stale window"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `services/shared/jwks_cache.py` committed
- [ ] Startup log shows `jwks_refreshed`
- [ ] Stopping Keycloak → auth requests still succeed (from cache)
- [ ] `jwks_refresh_failed_using_stale` warning appears in logs when Keycloak is down
- [ ] Restarting Keycloak → `jwks_refreshed` appears again

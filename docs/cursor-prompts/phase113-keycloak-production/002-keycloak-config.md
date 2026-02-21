# Phase 113 — Keycloak Production Start Mode + Health Check

## File to modify
`compose/docker-compose.yml` — keycloak service

## Step 1: Switch from start-dev to start

Find the keycloak service `command:` or `entrypoint:`. It likely contains
`start-dev`. Replace with `start`:

```yaml
  keycloak:
    command: start --import-realm
```

`start` mode differences from `start-dev`:
- Caches enabled (Infinispan)
- Verbose dev logging disabled
- Theme caching enabled
- Requires explicit hostname configuration (handled below)
- H2 dev database disabled (we already use Postgres — no change needed)

## Step 2: Fix hostname configuration

Remove any hardcoded IPs. All hostname config comes from env vars:

```yaml
  keycloak:
    environment:
      # Remove or replace:
      # KC_HOSTNAME: "192.168.10.53"   ← DELETE THIS

      # Replace with:
      KC_HOSTNAME: ${KC_HOSTNAME}
      KC_HOSTNAME_STRICT: "false"          # allows IP-based access in addition to hostname
      KC_HOSTNAME_STRICT_HTTPS: "false"    # allow HTTP on internal network (Caddy handles TLS)
      KC_HTTP_ENABLED: "true"              # keep — Caddy proxies HTTP internally
      KC_PROXY: edge                       # Keycloak is behind a reverse proxy (Caddy)
```

Add `KC_HOSTNAME=localhost` to `compose/.env` (already there from Phase 110).

## Step 3: Add health check

```yaml
  keycloak:
    healthcheck:
      test: ["CMD-SHELL",
        "exec 3<>/dev/tcp/localhost/8080 && echo -e 'GET /health/ready HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n' >&3 && cat <&3 | grep -q '200 OK'"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
```

Keycloak takes 30-60s to start in `start` mode — `start_period: 60s` prevents
false health failures during startup.

**Simpler alternative health check:**
```yaml
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
```

Use curl version if `curl` is available in the Keycloak image (it is in recent versions).

## Step 4: Update Keycloak dependency chain

Services that depend on Keycloak (ui, ingest) should wait for it to be healthy:

```yaml
  ui:
    depends_on:
      keycloak:
        condition: service_healthy
      migrator:
        condition: service_completed_successfully
      pgbouncer:
        condition: service_healthy
```

## Step 5: Export updated realm config

After Keycloak starts in production mode, export the realm to update
`compose/keycloak/realm-pulse.json`:

```bash
# Wait for Keycloak to be healthy
docker exec pulse-keycloak \
  /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm pulse \
  --users realm_file

docker cp pulse-keycloak:/tmp/export/pulse-realm.json \
  compose/keycloak/realm-pulse.json
```

This ensures the realm file reflects the production-mode Keycloak schema,
which may differ slightly from the dev-mode export.

## Step 6: Verify realm auto-import still works

On a fresh start, Keycloak should import the realm automatically via
`--import-realm`. Confirm:

```bash
docker logs pulse-keycloak 2>&1 | grep -i "import\|realm\|pulse"
```

Expected: `Realm 'pulse' imported` or similar.

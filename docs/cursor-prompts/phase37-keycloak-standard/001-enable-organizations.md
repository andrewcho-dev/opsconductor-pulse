# 001: Enable Keycloak Organizations Feature

## Task

Enable the Organizations feature in Keycloak by adding the startup flag.

## File to Modify

Find the Keycloak service in your docker-compose file (likely `compose/docker-compose.yml` or `docker-compose.yml`).

## Change

Update the Keycloak command to include `--features=organization`:

### Before

```yaml
keycloak:
  command:
    - start-dev
    - --import-realm
```

### After

```yaml
keycloak:
  command:
    - start-dev
    - --import-realm
    - --features=organization
```

## Apply the Change

```bash
# Navigate to project root
cd /home/opsconductor/simcloud

# Restart Keycloak with new config
docker compose up -d keycloak --force-recreate

# Wait for startup (30-60 seconds)
sleep 45

# Verify Keycloak is running
docker compose logs --tail=30 keycloak | grep -E "(started|ERROR)"

# Test Organizations API is now available
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse
```

## Expected Output

Before enabling, Organizations API returned:
```
Resource not found for url: .../organizations
```

After enabling, should return empty list:
```
[ ]
```

## Troubleshooting

If Keycloak fails to start:

```bash
# Check logs
docker compose logs keycloak

# Common issues:
# - Typo in feature name (must be exactly "organization")
# - Database migration issues (rare)
```

If Organizations API still returns 404:

```bash
# Verify the flag is in the running container
docker compose exec keycloak cat /proc/1/cmdline | tr '\0' '\n' | grep features

# Should show: --features=organization
```

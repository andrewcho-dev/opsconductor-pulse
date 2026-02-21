# 001a: Upgrade Keycloak to Version 26

## Problem

Keycloak 24.0 does not fully support Organizations feature.
The `--features=organization` flag is not recognized.

## Solution

Upgrade to Keycloak 26.x (latest stable) where Organizations is fully supported.

## Steps

### 1. Update Docker Compose

**File:** `compose/docker-compose.yml` (or wherever Keycloak is defined)

Find the Keycloak image line and update:

```yaml
# OLD
image: quay.io/keycloak/keycloak:24.0

# NEW
image: quay.io/keycloak/keycloak:26.0
```

### 2. Update Command with Organizations Feature

Also update the command to enable Organizations:

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:26.0
  command:
    - start-dev
    - --import-realm
    - --features=organization
  # ... rest of config unchanged
```

### 3. Backup Current State (Safety)

Before upgrading, export the current realm:

```bash
# Export current realm config
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get realms/pulse > /tmp/pulse_realm_backup.json

# Also backup users
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get users -r pulse > /tmp/pulse_users_backup.json

echo "Backups saved to /tmp/"
```

### 4. Stop and Upgrade

```bash
# Stop Keycloak
docker compose stop keycloak

# Remove old container (data is in volume, will persist)
docker compose rm -f keycloak

# Pull new image
docker compose pull keycloak

# Start with new version
docker compose up -d keycloak

# Watch logs for startup
docker compose logs -f keycloak
```

### 5. Wait for Migration

Keycloak will automatically migrate the database schema. This may take 1-2 minutes.

Watch for:
```
Keycloak 26.0.x ... started in Xs
```

### 6. Verify Upgrade

```bash
# Check version
docker compose exec keycloak /opt/keycloak/bin/kc.sh --version

# Login
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Test Organizations API (should return empty array now, not 404)
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse
```

Expected output:
```
[ ]
```

(Empty array = Organizations feature is working)

### 7. Verify Existing Data

```bash
# Check realm still exists
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get realms/pulse --fields realm,enabled

# Check users still exist
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get users -r pulse --fields username

# Check clients still exist
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r pulse --fields clientId
```

## Rollback (if needed)

If upgrade fails:

```bash
# Change image back to 24.0
# Edit docker-compose.yml: image: quay.io/keycloak/keycloak:24.0
# Remove --features=organization from command

docker compose stop keycloak
docker compose rm -f keycloak
docker compose up -d keycloak
```

Note: Database schema changes from 26 may not be backward compatible. If rolling back, you may need to restore from a database backup.

## After Successful Upgrade

Continue with:
- `002-create-roles.md`
- `003-create-organization.md`
- etc.

## Version History

| Version | Organizations Status |
|---------|---------------------|
| 24.0 | Preview (broken/incomplete) |
| 25.0 | Preview (functional) |
| 26.0 | **Stable/Supported** |

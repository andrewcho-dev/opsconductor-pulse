# 004: Fix Protocol Mappers

## Task

Replace the custom attribute-based mappers with standard organization and role mappers.

## Current State (Wrong)

```
pulse-ui client has:
- tenant_id mapper: reads user.attribute.tenant_id → claim tenant_id
- role mapper: reads user.attribute.role → claim role
```

These are broken because user attributes are empty.

## Target State (Correct)

```
pulse-ui client should have:
- organization mapper: maps org membership → claim organization
- realm roles mapper: maps realm roles → claim realm_access.roles
```

## Commands

```bash
# Login to Keycloak admin CLI
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Get pulse-ui client ID
CLIENT_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r pulse \
  -q clientId=pulse-ui --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
echo "Client ID: $CLIENT_ID"

# List current mappers
echo "=== Current Mappers ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  --fields name,protocolMapper

# Delete the old broken mappers
echo "=== Removing old mappers ==="

# Get and delete tenant_id mapper
TENANT_MAPPER_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  -q name=tenant_id --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
if [ -n "$TENANT_MAPPER_ID" ] && [ "$TENANT_MAPPER_ID" != "id" ]; then
  docker compose exec keycloak /opt/keycloak/bin/kcadm.sh delete clients/$CLIENT_ID/protocol-mappers/models/$TENANT_MAPPER_ID -r pulse
  echo "Deleted tenant_id mapper"
fi

# Get and delete role mapper (the attribute-based one)
ROLE_MAPPER_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  -q name=role --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
if [ -n "$ROLE_MAPPER_ID" ] && [ "$ROLE_MAPPER_ID" != "id" ]; then
  docker compose exec keycloak /opt/keycloak/bin/kcadm.sh delete clients/$CLIENT_ID/protocol-mappers/models/$ROLE_MAPPER_ID -r pulse
  echo "Deleted role mapper"
fi

# Create organization membership mapper
echo "=== Creating organization mapper ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  -s name=organization \
  -s protocol=openid-connect \
  -s protocolMapper=oidc-organization-membership-mapper \
  -s 'config."id.token.claim"=true' \
  -s 'config."access.token.claim"=true' \
  -s 'config."userinfo.token.claim"=true'

# Create realm roles mapper (standard, should already exist but ensure it's configured)
echo "=== Creating realm roles mapper ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  -s name=realm-roles \
  -s protocol=openid-connect \
  -s protocolMapper=oidc-usermodel-realm-role-mapper \
  -s 'config."claim.name"=realm_access.roles' \
  -s 'config."jsonType.label"=String' \
  -s 'config."multivalued"=true' \
  -s 'config."id.token.claim"=true' \
  -s 'config."access.token.claim"=true' \
  -s 'config."userinfo.token.claim"=true'

# Verify new mappers
echo "=== New Mappers ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  --fields name,protocolMapper
```

## Also Update pulse-api Client (if exists)

```bash
# Get pulse-api client ID
API_CLIENT_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r pulse \
  -q clientId=pulse-api --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')

if [ -n "$API_CLIENT_ID" ] && [ "$API_CLIENT_ID" != "id" ]; then
  echo "Updating pulse-api mappers..."

  # Add organization mapper to API client too
  docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create clients/$API_CLIENT_ID/protocol-mappers/models -r pulse \
    -s name=organization \
    -s protocol=openid-connect \
    -s protocolMapper=oidc-organization-membership-mapper \
    -s 'config."id.token.claim"=true' \
    -s 'config."access.token.claim"=true' \
    -s 'config."userinfo.token.claim"=true'
fi
```

## Expected Token Structure After Fix

```json
{
  "sub": "user-uuid",
  "preferred_username": "acme-admin",
  "organization": {
    "acme-industrial": {}
  },
  "realm_access": {
    "roles": ["customer", "tenant-admin", "default-roles-pulse"]
  }
}
```

## Verification

```bash
# Get a test token and decode it
# (You'll do this after user migration in step 005)
```

# 005: Migrate Users to Organizations and Roles

## Task

Assign existing users to the proper organizations and roles.

## User Mapping

| Username | Organization | Roles | Notes |
|----------|--------------|-------|-------|
| `operator1` | (none) | operator | System operator |
| `operator_admin` | (none) | operator, operator-admin | System admin |
| `acme-admin` | acme-industrial | customer, tenant-admin | Tenant admin |
| `customer1` | acme-industrial | customer | Regular user |
| `customer2` | acme-industrial | customer | Regular user |

## Commands

```bash
# Login to Keycloak admin CLI
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Get organization ID
ORG_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse \
  -q alias=acme-industrial --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
echo "Organization ID: $ORG_ID"

# ============================================
# 1. Operator Users (no organization, system roles)
# ============================================

echo "=== Setting up operator1 ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh add-roles -r pulse \
  --uusername operator1 \
  --rolename operator

echo "=== Setting up operator_admin ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh add-roles -r pulse \
  --uusername operator_admin \
  --rolename operator \
  --rolename operator-admin

# ============================================
# 2. Tenant Users (add to organization + roles)
# ============================================

# Helper function to add user to organization
add_user_to_org() {
  local username=$1
  local org_id=$2

  # Get user ID
  USER_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get users -r pulse \
    -q username=$username --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')

  if [ -n "$USER_ID" ] && [ "$USER_ID" != "id" ]; then
    echo "Adding $username to organization..."
    docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create organizations/$org_id/members -r pulse \
      -s userId=$USER_ID 2>/dev/null || echo "  (may already be a member)"
  else
    echo "User $username not found"
  fi
}

echo "=== Setting up acme-admin ==="
add_user_to_org "acme-admin" "$ORG_ID"
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh add-roles -r pulse \
  --uusername acme-admin \
  --rolename customer \
  --rolename tenant-admin

echo "=== Setting up customer1 ==="
add_user_to_org "customer1" "$ORG_ID"
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh add-roles -r pulse \
  --uusername customer1 \
  --rolename customer

echo "=== Setting up customer2 ==="
add_user_to_org "customer2" "$ORG_ID"
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh add-roles -r pulse \
  --uusername customer2 \
  --rolename customer

# ============================================
# 3. Verify organization membership
# ============================================

echo ""
echo "=== Organization Members ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations/$ORG_ID/members -r pulse \
  --fields username

# ============================================
# 4. Verify role assignments
# ============================================

echo ""
echo "=== User Role Verification ==="
for user in operator1 operator_admin acme-admin customer1 customer2; do
  echo "--- $user ---"
  USER_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get users -r pulse \
    -q username=$user --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
  docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get users/$USER_ID/role-mappings/realm -r pulse \
    --fields name 2>/dev/null | grep name || echo "  (no roles)"
done
```

## Reset User Passwords (if needed)

If any users need password reset:

```bash
# Reset acme-admin password
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh set-password -r pulse \
  --username acme-admin \
  --new-password acme123

# Reset customer1 password
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh set-password -r pulse \
  --username customer1 \
  --new-password customer123
```

## Expected Output

Organization Members:
```
[ { "username": "acme-admin" }, { "username": "customer1" }, { "username": "customer2" } ]
```

User Roles:
```
--- operator1 ---
  { "name": "operator" }
--- operator_admin ---
  { "name": "operator" }
  { "name": "operator-admin" }
--- acme-admin ---
  { "name": "customer" }
  { "name": "tenant-admin" }
--- customer1 ---
  { "name": "customer" }
--- customer2 ---
  { "name": "customer" }
```

## Test Token

After migration, test that tokens contain organization:

```bash
# Get a token for acme-admin
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/pulse/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=pulse-ui" \
  -d "username=acme-admin" \
  -d "password=acme123" | jq -r '.access_token')

# Decode and view (paste token at jwt.io or use jq)
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .

# Should show:
# "organization": { "acme-industrial": {} }
# "realm_access": { "roles": ["customer", "tenant-admin", ...] }
```

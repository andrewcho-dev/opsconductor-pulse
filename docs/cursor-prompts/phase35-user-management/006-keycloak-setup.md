# 006: Keycloak Realm Configuration

## Task

Configure Keycloak realm with required roles and client settings for user management.

## Prerequisites

- Keycloak running at `http://localhost:8080` (or via ingress at `/auth`)
- Admin credentials available

## Configuration Steps

### 1. Create Realm Roles

Execute via Keycloak Admin Console or API:

**Using Admin Console:**
1. Login to Keycloak Admin Console
2. Select realm: `iotcloud`
3. Go to Realm roles → Create role

**Create these roles:**

| Role | Description |
|------|-------------|
| `operator` | System operator - can view and manage all tenants |
| `operator-admin` | System admin - can create operators and full system access |
| `tenant-admin` | Tenant admin - can manage users within their tenant |
| `customer` | Regular tenant user - standard access |

**Using Keycloak Admin API (script):**

**File:** `scripts/keycloak/setup-roles.sh` (NEW)

```bash
#!/bin/bash
set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-iotcloud}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

echo "Getting admin token..."
TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASS}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Failed to get admin token"
  exit 1
fi

echo "Token obtained successfully"

# Function to create role if not exists
create_role() {
  local role_name=$1
  local description=$2

  # Check if role exists
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/roles/${role_name}")

  if [ "$status" == "200" ]; then
    echo "Role '${role_name}' already exists"
    return
  fi

  echo "Creating role: ${role_name}"
  curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/roles" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${role_name}\",
      \"description\": \"${description}\"
    }"

  echo "Created role: ${role_name}"
}

# Create application roles
create_role "operator" "System operator - view and manage all tenants"
create_role "operator-admin" "System admin - create operators and full system access"
create_role "tenant-admin" "Tenant admin - manage users within tenant"
create_role "customer" "Regular tenant user - standard access"

echo ""
echo "Roles created successfully!"
echo ""
echo "Verifying roles..."
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/roles" | jq '.[].name'
```

### 2. Configure Client for Service Account

The UI backend needs a service account to call Keycloak Admin API.

**Option A: Use admin credentials (simpler, for dev/test)**

Already configured in `001-keycloak-admin-service.md` using username/password.

**Option B: Use dedicated service account (recommended for production)**

**File:** `scripts/keycloak/setup-service-account.sh` (NEW)

```bash
#!/bin/bash
set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-iotcloud}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
CLIENT_ID="${SERVICE_ACCOUNT_CLIENT_ID:-iot-admin-service}"
CLIENT_SECRET="${SERVICE_ACCOUNT_CLIENT_SECRET:-}"

# Get admin token
TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASS}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

echo "Creating service account client: ${CLIENT_ID}"

# Generate secret if not provided
if [ -z "$CLIENT_SECRET" ]; then
  CLIENT_SECRET=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
fi

# Create client
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"clientId\": \"${CLIENT_ID}\",
    \"name\": \"IoT Admin Service\",
    \"description\": \"Service account for backend user management\",
    \"enabled\": true,
    \"clientAuthenticatorType\": \"client-secret\",
    \"secret\": \"${CLIENT_SECRET}\",
    \"serviceAccountsEnabled\": true,
    \"directAccessGrantsEnabled\": false,
    \"standardFlowEnabled\": false,
    \"publicClient\": false,
    \"protocol\": \"openid-connect\"
  }"

# Get client internal ID
CLIENT_UUID=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" | jq -r '.[0].id')

if [ "$CLIENT_UUID" == "null" ] || [ -z "$CLIENT_UUID" ]; then
  echo "Failed to get client UUID"
  exit 1
fi

echo "Client created with UUID: ${CLIENT_UUID}"

# Get service account user
SA_USER_ID=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/${CLIENT_UUID}/service-account-user" | jq -r '.id')

echo "Service account user ID: ${SA_USER_ID}"

# Get realm-management client roles
REALM_MGMT_CLIENT_UUID=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=realm-management" | jq -r '.[0].id')

# Get required roles for user management
ROLES_TO_ASSIGN='["manage-users", "view-users", "query-users", "view-realm"]'

for role_name in manage-users view-users query-users view-realm; do
  ROLE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/${REALM_MGMT_CLIENT_UUID}/roles/${role_name}")

  echo "Assigning role: ${role_name}"
  curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/users/${SA_USER_ID}/role-mappings/clients/${REALM_MGMT_CLIENT_UUID}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "[${ROLE}]"
done

echo ""
echo "Service account configured successfully!"
echo ""
echo "Add these to your environment:"
echo "  KEYCLOAK_ADMIN_CLIENT_ID=${CLIENT_ID}"
echo "  KEYCLOAK_ADMIN_CLIENT_SECRET=${CLIENT_SECRET}"
```

### 3. Update Keycloak Client Service for Client Credentials

**File:** `services/ui_iot/services/keycloak_admin.py`

If using service account (Option B), update the token acquisition:

```python
async def _get_admin_token(self) -> str:
    """Get admin access token using client credentials."""
    # Check if we have a valid cached token
    if self._token and self._token_expires:
        if datetime.now(timezone.utc) < self._token_expires:
            return self._token

    # Determine auth method
    client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID")
    client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")

    if client_id and client_secret:
        # Use client credentials (service account)
        token_url = f"{KEYCLOAK_ADMIN_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    else:
        # Fall back to password auth (admin user)
        token_url = f"{KEYCLOAK_ADMIN_URL}/realms/master/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USERNAME,
            "password": KEYCLOAK_ADMIN_PASSWORD,
        }

    response = await self._client.post(token_url, data=data)
    response.raise_for_status()

    data = response.json()
    self._token = data["access_token"]
    expires_in = data.get("expires_in", 300) - 60
    self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return self._token
```

### 4. Environment Configuration

**File:** `.env.example`

Add these variables:

```bash
# Keycloak Admin Configuration
KEYCLOAK_ADMIN_URL=http://keycloak:8080
KEYCLOAK_REALM=iotcloud

# Option A: Username/password auth (development)
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# Option B: Service account (production)
# KEYCLOAK_ADMIN_CLIENT_ID=iot-admin-service
# KEYCLOAK_ADMIN_CLIENT_SECRET=your-client-secret
```

**File:** `docker-compose.yml`

Add to ui_iot service:

```yaml
ui_iot:
  environment:
    - KEYCLOAK_ADMIN_URL=http://keycloak:8080
    - KEYCLOAK_REALM=iotcloud
    - KEYCLOAK_ADMIN_USERNAME=${KEYCLOAK_ADMIN_USERNAME:-admin}
    - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin}
```

### 5. Default User Setup (Development)

**File:** `scripts/keycloak/setup-default-users.sh` (NEW)

```bash
#!/bin/bash
set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-iotcloud}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

# Get admin token
TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASS}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

# Function to create user
create_user() {
  local username=$1
  local email=$2
  local first_name=$3
  local last_name=$4
  local password=$5
  local tenant_id=$6

  echo "Creating user: ${username}"

  # Build attributes
  local attributes="{}"
  if [ -n "$tenant_id" ]; then
    attributes="{\"tenant_id\": [\"${tenant_id}\"]}"
  fi

  curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/users" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"${username}\",
      \"email\": \"${email}\",
      \"firstName\": \"${first_name}\",
      \"lastName\": \"${last_name}\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"attributes\": ${attributes},
      \"credentials\": [{
        \"type\": \"password\",
        \"value\": \"${password}\",
        \"temporary\": false
      }]
    }"
}

# Function to assign role
assign_role() {
  local username=$1
  local role_name=$2

  # Get user ID
  local user_id=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/users?username=${username}&exact=true" | jq -r '.[0].id')

  if [ "$user_id" == "null" ] || [ -z "$user_id" ]; then
    echo "User ${username} not found"
    return
  fi

  # Get role
  local role=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/roles/${role_name}")

  echo "Assigning role ${role_name} to ${username}"
  curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/users/${user_id}/role-mappings/realm" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "[${role}]"
}

# Create operator users
create_user "sysadmin" "sysadmin@opsconductor.local" "System" "Admin" "admin123" ""
assign_role "sysadmin" "operator-admin"
assign_role "sysadmin" "operator"

create_user "operator1" "operator1@opsconductor.local" "First" "Operator" "operator123" ""
assign_role "operator1" "operator"

# Create tenant admin users (example tenants)
create_user "acme-admin" "admin@acme.example" "Acme" "Admin" "acme123" "acme-corp"
assign_role "acme-admin" "tenant-admin"
assign_role "acme-admin" "customer"

create_user "acme-user" "user@acme.example" "Acme" "User" "user123" "acme-corp"
assign_role "acme-user" "customer"

echo ""
echo "Default users created!"
echo ""
echo "Operator users:"
echo "  sysadmin / admin123 (operator-admin)"
echo "  operator1 / operator123 (operator)"
echo ""
echo "Tenant users (acme-corp):"
echo "  acme-admin / acme123 (tenant-admin)"
echo "  acme-user / user123 (customer)"
```

### 6. User Attribute Mapper for tenant_id

Configure Keycloak to include tenant_id in access tokens:

**File:** `scripts/keycloak/setup-mappers.sh` (NEW)

```bash
#!/bin/bash
set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-iotcloud}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
CLIENT_ID="${FRONTEND_CLIENT_ID:-iot-frontend}"

# Get admin token
TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASS}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

# Get client UUID
CLIENT_UUID=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" | jq -r '.[0].id')

if [ "$CLIENT_UUID" == "null" ] || [ -z "$CLIENT_UUID" ]; then
  echo "Client ${CLIENT_ID} not found"
  exit 1
fi

echo "Creating tenant_id mapper for client: ${CLIENT_ID}"

# Create protocol mapper for tenant_id
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/${CLIENT_UUID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tenant_id",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usermodel-attribute-mapper",
    "consentRequired": false,
    "config": {
      "userinfo.token.claim": "true",
      "user.attribute": "tenant_id",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "claim.name": "tenant_id",
      "jsonType.label": "String",
      "multivalued": "false"
    }
  }'

echo "Creating realm roles mapper..."

# Create realm roles mapper
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/${CLIENT_UUID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "realm roles",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usermodel-realm-role-mapper",
    "consentRequired": false,
    "config": {
      "userinfo.token.claim": "true",
      "id.token.claim": "true",
      "access.token.claim": "true",
      "claim.name": "roles",
      "jsonType.label": "String",
      "multivalued": "true"
    }
  }'

echo ""
echo "Protocol mappers configured!"
echo "Tokens will now include 'tenant_id' and 'roles' claims"
```

### 7. Master Setup Script

**File:** `scripts/keycloak/setup-all.sh` (NEW)

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Keycloak User Management Setup"
echo "=========================================="
echo ""

# Wait for Keycloak to be ready
echo "Waiting for Keycloak..."
until curl -s -o /dev/null "${KEYCLOAK_URL:-http://localhost:8080}/health/ready"; do
  sleep 2
done
echo "Keycloak is ready"
echo ""

# Run setup scripts in order
echo "1. Setting up roles..."
bash "${SCRIPT_DIR}/setup-roles.sh"
echo ""

echo "2. Setting up protocol mappers..."
bash "${SCRIPT_DIR}/setup-mappers.sh"
echo ""

echo "3. Setting up default users..."
bash "${SCRIPT_DIR}/setup-default-users.sh"
echo ""

# Optional: Setup service account for production
if [ "${SETUP_SERVICE_ACCOUNT:-false}" == "true" ]; then
  echo "4. Setting up service account..."
  bash "${SCRIPT_DIR}/setup-service-account.sh"
  echo ""
fi

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
```

## Makefile Target

**File:** `Makefile`

Add target:

```makefile
.PHONY: setup-keycloak-users
setup-keycloak-users:
	@echo "Setting up Keycloak for user management..."
	docker compose exec -T keycloak /bin/bash -c 'apt-get update && apt-get install -y jq curl' || true
	KEYCLOAK_URL=http://localhost:8080 \
	KEYCLOAK_REALM=iotcloud \
	KEYCLOAK_ADMIN=admin \
	KEYCLOAK_ADMIN_PASSWORD=admin \
	bash scripts/keycloak/setup-all.sh
```

## Verification

```bash
# Run the setup
make setup-keycloak-users

# Or manually:
cd scripts/keycloak
KEYCLOAK_URL=http://localhost:8080 ./setup-all.sh

# Verify roles exist
curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token' | xargs -I{} \
  curl -s -H "Authorization: Bearer {}" \
  "http://localhost:8080/admin/realms/iotcloud/roles" | jq '.[].name'

# Expected output:
# "operator"
# "operator-admin"
# "tenant-admin"
# "customer"

# Verify default users
curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token' | xargs -I{} \
  curl -s -H "Authorization: Bearer {}" \
  "http://localhost:8080/admin/realms/iotcloud/users" | jq '.[].username'

# Test login as operator
curl -s -X POST "http://localhost:8080/realms/iotcloud/protocol/openid-connect/token" \
  -d "username=sysadmin" \
  -d "password=admin123" \
  -d "grant_type=password" \
  -d "client_id=iot-frontend" | jq '.'
```

## Files Created

| File | Purpose |
|------|---------|
| `scripts/keycloak/setup-roles.sh` | Create realm roles |
| `scripts/keycloak/setup-mappers.sh` | Configure token claims |
| `scripts/keycloak/setup-default-users.sh` | Create default users |
| `scripts/keycloak/setup-service-account.sh` | Optional production setup |
| `scripts/keycloak/setup-all.sh` | Master setup script |

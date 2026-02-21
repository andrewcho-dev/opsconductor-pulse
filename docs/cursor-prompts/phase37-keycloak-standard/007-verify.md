# 007: End-to-End Verification

## Task

Verify the entire Keycloak standardization is working correctly.

## Checklist

### 1. Keycloak Configuration

```bash
# Login
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Verify Organizations feature is enabled
echo "=== Organizations ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse --fields name,alias

# Verify roles exist
echo "=== Roles ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get roles -r pulse --fields name | grep -E "(operator|customer|tenant)"

# Verify organization membership
ORG_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse \
  -q alias=acme-industrial --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
echo "=== Organization Members ==="
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations/$ORG_ID/members -r pulse --fields username
```

Expected:
- Organizations: `acme-industrial`
- Roles: `operator`, `operator-admin`, `tenant-admin`, `customer`
- Members: `acme-admin`, `customer1`, `customer2`

### 2. Token Contents

```bash
# Get token for acme-admin (tenant user)
ACME_TOKEN=$(curl -s -X POST "http://localhost:8080/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=pulse-ui" \
  -d "username=acme-admin" \
  -d "password=acme123" | jq -r '.access_token')

echo "=== Acme Admin Token ==="
echo $ACME_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq '{
  preferred_username,
  organization,
  realm_access
}'

# Get token for operator1 (system user)
OP_TOKEN=$(curl -s -X POST "http://localhost:8080/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=pulse-ui" \
  -d "username=operator1" \
  -d "password=YOUR_OPERATOR_PASSWORD" | jq -r '.access_token')

echo "=== Operator Token ==="
echo $OP_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq '{
  preferred_username,
  organization,
  realm_access
}'
```

Expected acme-admin token:
```json
{
  "preferred_username": "acme-admin",
  "organization": {
    "acme-industrial": {}
  },
  "realm_access": {
    "roles": ["customer", "tenant-admin", "default-roles-pulse", ...]
  }
}
```

Expected operator token:
```json
{
  "preferred_username": "operator1",
  "organization": null,
  "realm_access": {
    "roles": ["operator", "default-roles-pulse", ...]
  }
}
```

### 3. API Access Control

```bash
# Tenant user can access their devices
echo "=== Tenant User - Own Devices ==="
curl -s -H "Authorization: Bearer $ACME_TOKEN" \
  https://YOUR_HOST/customer/devices | jq '.devices | length'
# Expected: 12 (or number of acme-industrial devices)

# Tenant user cannot access operator endpoints
echo "=== Tenant User - Operator Endpoint (should fail) ==="
curl -s -H "Authorization: Bearer $ACME_TOKEN" \
  https://YOUR_HOST/operator/tenants | jq '.error // .detail'
# Expected: 403 Forbidden

# Operator can access all tenants
echo "=== Operator - All Tenants ==="
curl -s -H "Authorization: Bearer $OP_TOKEN" \
  https://YOUR_HOST/operator/tenants | jq '.tenants | length'
# Expected: 1 (or total tenant count)
```

### 4. UI Verification

Manual testing in browser:

#### As acme-admin:
1. Login with `acme-admin` / `acme123`
2. Should see customer portal (not operator portal)
3. Should see only Acme Industrial devices (12)
4. Should see "Settings > Users" if tenant-admin (Phase 35 UI)
5. Should NOT see operator menu items

#### As operator1:
1. Login with `operator1` / `<password>`
2. Should see operator portal
3. Should see all tenants in system
4. Should see all devices across tenants
5. Should see "Users" in operator menu (Phase 35 UI)

### 5. Database Alignment

```bash
# Verify tenant_id in database matches org alias
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT tenant_id, name FROM tenants;
"
# Should show: acme-industrial | Acme Industrial

# Verify devices belong to correct tenant
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT tenant_id, COUNT(*) as device_count
FROM device_registry
GROUP BY tenant_id;
"
# Should show: acme-industrial | 12
```

## Troubleshooting

### Token missing organization claim

Check protocol mappers:
```bash
CLIENT_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r pulse \
  -q clientId=pulse-ui --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients/$CLIENT_ID/protocol-mappers/models -r pulse \
  --fields name,protocolMapper | grep -A1 organization
```

Should show `oidc-organization-membership-mapper`.

### User not seeing their tenant data

Check organization membership:
```bash
ORG_ID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations -r pulse \
  -q alias=acme-industrial --fields id --format csv 2>/dev/null | tail -1 | tr -d '"')
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get organizations/$ORG_ID/members -r pulse
```

### Backend returning wrong tenant

Check the `get_tenant_id()` function is reading from `organization` not `tenant_id` attribute.

## Success Criteria

- [ ] Organizations feature enabled
- [ ] acme-industrial organization exists
- [ ] Roles created: operator, operator-admin, tenant-admin, customer
- [ ] Users assigned to correct organizations
- [ ] Tokens contain `organization` claim
- [ ] Tokens contain `realm_access.roles`
- [ ] Tenant users see only their data
- [ ] Operators see all data
- [ ] UI shows correct menus for each role

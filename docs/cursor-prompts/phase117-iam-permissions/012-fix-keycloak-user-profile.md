# 012 — Fix Keycloak User Profile: declare `tenant_id` attribute

## Bug

Keycloak 26 uses "declarative user profile" (enabled by default since KC 24). Only attributes explicitly declared in the user profile configuration are accepted via the Admin REST API. The `tenant_id` attribute is **not declared**, so:

1. `PUT /admin/realms/pulse/users/{id}` with `attributes: {"tenant_id": [...]}` → silently drops `tenant_id`
2. `POST /admin/realms/pulse/users` with `attributes: {"tenant_id": [...]}` → silently drops `tenant_id`
3. `GET /admin/realms/pulse/users/{id}` → omits `attributes` entirely for users missing profile-declared attrs
4. `GET /admin/realms/pulse/users` (list) → includes `attributes` only for users imported via realm JSON (which bypasses profile validation)

### Impact

- **Invite flow broken**: `POST /customer/users/invite` creates user via `create_user()` with `attributes={"tenant_id": [tenant_id]}` (line 733 of `routes/users.py`), but Keycloak drops the attribute → invited user is invisible to their tenant
- **Single-user GET missing attributes**: This was the root cause of Fix 010 (the fallback in `keycloak_admin.py:get_user()`) — with this fix, the fallback becomes unnecessary (though keeping it is fine as defense-in-depth)

### Why customer1 works

`customer1` was created via realm JSON import (`realm-pulse.json`), which bypasses user profile validation. So their `tenant_id` attribute persists.

## Fix: `compose/keycloak/realm-pulse.json`

Add `userProfile` configuration at the top level of the realm JSON, declaring `tenant_id` as an admin-managed attribute.

### Add after the `"smtpServer": { ... }` block (before `"users":`):

```json
  "attributes": {
    "userProfileEnabled": "true"
  },
  "userProfile": {
    "attributes": [
      {
        "name": "username",
        "displayName": "${username}",
        "validations": {
          "length": { "min": 3, "max": 255 },
          "username-prohibited-characters": {},
          "up-username-not-idn-homograph": {}
        },
        "permissions": {
          "view": ["admin", "user"],
          "edit": ["admin", "user"]
        },
        "multivalued": false
      },
      {
        "name": "email",
        "displayName": "${email}",
        "validations": {
          "email": {},
          "length": { "max": 255 }
        },
        "required": { "roles": ["user"] },
        "permissions": {
          "view": ["admin", "user"],
          "edit": ["admin", "user"]
        },
        "multivalued": false
      },
      {
        "name": "firstName",
        "displayName": "${firstName}",
        "validations": {
          "length": { "max": 255 },
          "person-name-prohibited-characters": {}
        },
        "required": { "roles": ["user"] },
        "permissions": {
          "view": ["admin", "user"],
          "edit": ["admin", "user"]
        },
        "multivalued": false
      },
      {
        "name": "lastName",
        "displayName": "${lastName}",
        "validations": {
          "length": { "max": 255 },
          "person-name-prohibited-characters": {}
        },
        "required": { "roles": ["user"] },
        "permissions": {
          "view": ["admin", "user"],
          "edit": ["admin", "user"]
        },
        "multivalued": false
      },
      {
        "name": "tenant_id",
        "displayName": "Tenant ID",
        "permissions": {
          "view": ["admin"],
          "edit": ["admin"]
        },
        "multivalued": false
      }
    ],
    "groups": [
      {
        "name": "user-metadata",
        "displayHeader": "User metadata",
        "displayDescription": "Attributes, which refer to user metadata"
      }
    ]
  },
```

### Runtime fix (already applied)

The `tenant_id` attribute was already added to the live Keycloak user profile via the Admin API:

```
PUT /admin/realms/pulse/users/profile
```

And customer2's `tenant_id` was set to `["acme-industrial"]`. This persists in Keycloak's internal DB until the container volume is destroyed.

### Important: realm JSON vs runtime

The `realm-pulse.json` file is only consumed during **initial realm import** (first Keycloak boot with an empty DB, or when `--import-realm` is used). It does NOT re-apply on subsequent container restarts against an existing Keycloak volume.

**For existing deployments**, the user profile must be updated via the Admin API:

```bash
# 1. Get admin token
TOKEN=$(curl -s -X POST http://pulse-keycloak:8080/realms/master/protocol/openid-connect/token \
  -d "grant_type=password&client_id=admin-cli&username=admin&password=$KC_BOOTSTRAP_ADMIN_PASSWORD" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Get current user profile
PROFILE=$(curl -s http://pulse-keycloak:8080/admin/realms/pulse/users/profile \
  -H "Authorization: Bearer $TOKEN")

# 3. Add tenant_id attribute (use jq or python to append to attributes array)
UPDATED=$(echo "$PROFILE" | python3 -c "
import sys, json
p = json.load(sys.stdin)
names = [a['name'] for a in p['attributes']]
if 'tenant_id' not in names:
    p['attributes'].append({
        'name': 'tenant_id',
        'displayName': 'Tenant ID',
        'permissions': {'view': ['admin'], 'edit': ['admin']},
        'multivalued': False
    })
print(json.dumps(p))
")

# 4. Update user profile
curl -s -X PUT http://pulse-keycloak:8080/admin/realms/pulse/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPDATED"
```

This script is idempotent — safe to run multiple times. Consider adding it to `scripts/seed_demo_data.py` or a dedicated Keycloak post-bootstrap script.

## Verification

### Verified (2026-02-16)

1. **Invite flow**: `POST /customer/users/invite` → user created with `tenant_id=["acme-industrial"]` ✓
2. **Single-user GET**: `GET /admin/realms/pulse/users/{id}` returns `attributes` with `tenant_id` ✓
3. **Tenant user list**: `GET /customer/users` returns all 3 tenant users (customer1, customer2, testinvite) ✓
4. **Cleanup**: testinvite user deleted after verification

### Fresh bootstrap verification

After `docker compose down -v && docker compose up`:
- All 4 users should have `tenant_id` attributes (from realm JSON import)
- `GET /admin/realms/pulse/users/{id}` should return `attributes` key for all users
- `POST /customer/users/invite` should create users with correct `tenant_id`

# 003 — Rotate Keycloak Secrets and Remove Test Users

## Goal

1. Replace the hardcoded `pulse-api` client secret in realm-pulse.json
2. Remove or secure the 4 test users with password `test123`
3. Update the running Keycloak instance

## Part A — Fix realm-pulse.json (for future imports)

### File to Modify

`compose/keycloak/realm-pulse.json`

### Change 1 — Client Secret

Find the `pulse-api` client block and replace the hardcoded secret:

Find:
```json
"secret": "pulse-api-secret-dev"
```

Replace with:
```json
"secret": "${env.KEYCLOAK_CLIENT_SECRET}"
```

This makes Keycloak read the client secret from an environment variable.

Then add to `compose/.env`:
```
KEYCLOAK_CLIENT_SECRET=<value from step 001>
```

And add to the `keycloak` service in `docker-compose.yml` environment:
```yaml
  keycloak:
    environment:
      # ... existing vars ...
      KEYCLOAK_CLIENT_SECRET: ${KEYCLOAK_CLIENT_SECRET}
```

### Change 2 — Remove Test User Passwords

Find ALL user blocks with `"value": "test123"` and either:

**Option A (recommended): Remove the credentials block entirely.**
Users will have no password. Admins must set passwords via Keycloak
admin console after deployment.

```json
{
  "username": "customer1",
  "enabled": true,
  "credentials": []
}
```

**Option B: Mark passwords as temporary.**
Users will be forced to change password on first login.

```json
{
  "credentials": [
    { "type": "password", "value": "test123", "temporary": true }
  ]
}
```

**Affected users:** customer1, customer2, operator1, operator_admin

## Part B — Update the Running Keycloak Instance

The realm-pulse.json is only used on initial import. Since Keycloak is
already running with the imported data, you must also update the live
instance.

### Rotate the pulse-api Client Secret

```bash
# Get an admin token
ADMIN_TOKEN=$(curl -s -X POST \
  "https://pulse.enabledconsultants.com/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=<CURRENT_KEYCLOAK_ADMIN_PASSWORD>" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Get the pulse-api client ID (internal UUID)
CLIENT_UUID=$(curl -s \
  "https://pulse.enabledconsultants.com/admin/realms/pulse/clients?clientId=pulse-api" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Generate and set a new client secret
curl -s -X POST \
  "https://pulse.enabledconsultants.com/admin/realms/pulse/clients/$CLIENT_UUID/client-secret" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Retrieve the new secret (save this!)
NEW_SECRET=$(curl -s \
  "https://pulse.enabledconsultants.com/admin/realms/pulse/clients/$CLIENT_UUID/client-secret" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['value'])")

echo "New pulse-api client secret: $NEW_SECRET"
```

Update `KEYCLOAK_CLIENT_SECRET` in `.env` with this new value if it
differs from the one generated in step 001.

### Reset Test User Passwords

For each user (customer1, customer2, operator1, operator_admin):

```bash
# Get user UUID
USER_UUID=$(curl -s \
  "https://pulse.enabledconsultants.com/admin/realms/pulse/users?username=customer1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Option A: Disable the user
curl -s -X PUT \
  "https://pulse.enabledconsultants.com/admin/realms/pulse/users/$USER_UUID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Option B: Set a strong password (temporary — forces change on login)
curl -s -X PUT \
  "https://pulse.enabledconsultants.com/admin/realms/pulse/users/$USER_UUID/reset-password" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "password", "value": "<STRONG_PASSWORD>", "temporary": true}'
```

Repeat for all 4 test users.

## Notes

- If `pulse-api` client secret is used by any backend service, update
  that service's environment variable too. Check docker-compose.yml for
  any `KEYCLOAK_CLIENT_SECRET` references.
- After rotating the admin password (step 002), use the NEW admin
  password in the curl commands above.
- Consider whether the test users are needed at all in production. If
  not, delete them entirely via the Keycloak admin console.

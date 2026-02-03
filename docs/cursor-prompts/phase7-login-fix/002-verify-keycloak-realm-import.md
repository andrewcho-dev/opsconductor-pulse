# Task 002: Verify Keycloak Realm Import and User Provisioning

> **CURSOR: EXECUTE THIS TASK**
>
> This task requires you to RUN commands, not just write code.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Keycloak uses a realm import file (`compose/keycloak/realm-pulse.json`) to bootstrap the `pulse` realm, clients, and test users. But Keycloak only imports on first startup — if the realm already exists in the database, the import file is silently ignored. This means changes to `realm-pulse.json` (like updated redirect URIs from Task 001) may not take effect.

This task ensures the realm is properly imported with the correct configuration.

**Read first**:
- `compose/keycloak/realm-pulse.json` (full file)
- `compose/docker-compose.yml` (keycloak service)

---

## Task

### 2.1 Force Keycloak to re-import the realm

```bash
cd compose

# Stop all services
docker compose down

# Delete Keycloak's persisted data in Postgres so the realm re-imports
# (Keycloak stores realm config in the same Postgres as our app)
docker compose up -d postgres
sleep 3

# Delete Keycloak-specific tables so it re-imports
docker compose exec postgres psql -U iot -d iotcloud -c "
DO \$\$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'kc_%')
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
    -- Also drop Keycloak's other tables
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND (
        tablename LIKE 'admin_%' OR
        tablename LIKE 'authentication_%' OR
        tablename LIKE 'broker_%' OR
        tablename LIKE 'client_%' OR
        tablename LIKE 'component_%' OR
        tablename LIKE 'composite_%' OR
        tablename LIKE 'credential%' OR
        tablename LIKE 'databasechangelog%' OR
        tablename LIKE 'default_%' OR
        tablename LIKE 'event_%' OR
        tablename LIKE 'fed_%' OR
        tablename LIKE 'federated_%' OR
        tablename LIKE 'group_%' OR
        tablename LIKE 'identity_%' OR
        tablename LIKE 'migration_%' OR
        tablename LIKE 'offline_%' OR
        tablename LIKE 'policy_%' OR
        tablename LIKE 'protocol_%' OR
        tablename LIKE 'realm%' OR
        tablename LIKE 'redirect_%' OR
        tablename LIKE 'required_%' OR
        tablename LIKE 'resource_%' OR
        tablename LIKE 'revoked_%' OR
        tablename LIKE 'role_%' OR
        tablename LIKE 'scope_%' OR
        tablename LIKE 'single_%' OR
        tablename LIKE 'user_%' OR
        tablename LIKE 'username_%' OR
        tablename LIKE 'web_%'
    ))
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END\$\$;
"
```

**Alternative simpler approach** — if the above is too aggressive, just wipe the postgres data volume:

```bash
cd compose
docker compose down -v
docker compose up -d
```

This nukes all data (postgres volume included) and starts fresh. You'll need to re-run any seed data scripts afterward. This is the cleanest approach for development.

### 2.2 Wait for Keycloak to start and import the realm

```bash
cd compose
docker compose up -d

# Wait for Keycloak to be healthy
for i in $(seq 1 60); do
    if curl -sf http://localhost:8180/realms/pulse/.well-known/openid-configuration > /dev/null 2>&1; then
        echo "Keycloak ready with pulse realm"
        break
    fi
    echo "Waiting for Keycloak... ($i/60)"
    sleep 2
done
```

### 2.3 Verify the realm configuration

```bash
# 1. Verify the pulse realm exists
curl -sf http://localhost:8180/realms/pulse | python3 -c "import sys,json; d=json.load(sys.stdin); print('Realm:', d.get('realm'), 'Enabled:', d.get('enabled'))"

# 2. Get an admin token
ADMIN_TOKEN=$(curl -sf -X POST http://localhost:8180/realms/master/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=admin-cli" \
    -d "username=admin" \
    -d "password=admin_dev" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Verify the pulse-ui client exists and has correct redirect URIs
curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
    http://localhost:8180/admin/realms/pulse/clients?clientId=pulse-ui | \
    python3 -c "
import sys, json
clients = json.load(sys.stdin)
if clients:
    c = clients[0]
    print('Client:', c['clientId'])
    print('Redirect URIs:', c.get('redirectUris', []))
    print('Web Origins:', c.get('webOrigins', []))
    print('Public:', c.get('publicClient'))
    print('PKCE:', c.get('attributes', {}).get('pkce.code.challenge.method'))
else:
    print('ERROR: pulse-ui client not found!')
"

# 4. Verify test users exist
for user in customer1 customer2 operator1 operator_admin; do
    echo -n "User $user: "
    curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" \
        "http://localhost:8180/admin/realms/pulse/users?username=$user&exact=true" | \
        python3 -c "
import sys, json
users = json.load(sys.stdin)
if users:
    u = users[0]
    attrs = u.get('attributes', {})
    print('EXISTS, tenant_id=' + str(attrs.get('tenant_id', ['?'])), 'role=' + str(attrs.get('role', ['?'])))
else:
    print('NOT FOUND')
"
done

# 5. Verify token acquisition works
curl -sf -X POST http://localhost:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
token = data['access_token']
payload = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
print('Token OK')
print('  iss:', payload['iss'])
print('  aud:', payload.get('aud'))
print('  tenant_id:', payload.get('tenant_id'))
print('  role:', payload.get('role'))
print('  email:', payload.get('email'))
"
```

### 2.4 If any verification fails

**If the realm doesn't exist**: Check Keycloak logs for import errors:
```bash
docker compose logs keycloak | tail -50
```

**If users don't exist**: The realm JSON must include the users section. Check `compose/keycloak/realm-pulse.json` has a `users` array with customer1, customer2, operator1, operator_admin.

**If the token `iss` doesn't match expected hostname**: Verify `KC_HOSTNAME_URL` in docker-compose.yml matches `KEYCLOAK_URL`.

**If redirect URIs are wrong**: The realm was imported before the JSON was updated. You must delete the realm and re-import (use `docker compose down -v && docker compose up -d`).

---

## Test

### Step 1: Verify login flow end-to-end via curl

```bash
# Get the login redirect URL
REDIRECT=$(curl -sf -o /dev/null -w "%{redirect_url}" http://localhost:8080/login)
echo "Login redirects to: $REDIRECT"

# Verify it uses localhost (not pulse-keycloak or 192.168.10.53)
echo "$REDIRECT" | grep -q "localhost:8180" && echo "PASS: Keycloak URL is localhost" || echo "FAIL: Wrong Keycloak hostname in redirect"

# Verify redirect_uri parameter uses localhost
echo "$REDIRECT" | grep -q "redirect_uri=http%3A%2F%2Flocalhost%3A8080" && echo "PASS: Callback URL is localhost" || echo "FAIL: Wrong callback hostname in redirect"
```

### Step 2: Run integration tests

```bash
pytest tests/ -v --ignore=tests/e2e -x
```

### Step 3: Run E2E tests

```bash
KEYCLOAK_URL=http://localhost:8180 UI_BASE_URL=http://localhost:8080 RUN_E2E=1 pytest tests/ -v -x
```

### Step 4: Manual browser test

Open http://localhost:8080 in a browser:
1. Should redirect to Keycloak login at `http://localhost:8180/...`
2. Login with `customer1` / `test123`
3. Should redirect to `http://localhost:8080/customer/dashboard`
4. Dashboard should load with device data

**If you cannot open a browser** (e.g., SSH-only server), report the curl test results from Step 1 as evidence.

---

## Acceptance Criteria

- [ ] Keycloak pulse realm exists and is enabled
- [ ] pulse-ui client has correct redirect URIs
- [ ] Test users exist (customer1, customer2, operator1, operator_admin)
- [ ] Token acquisition works with correct `iss` claim
- [ ] Login redirect uses consistent hostname
- [ ] Callback redirect_uri uses same hostname as browser
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)
- [ ] Browser login works OR curl verification passes

**This task is not complete until Keycloak is verified healthy AND login flow works.**

---

## Commit

```
Verify Keycloak realm import and fix configuration

- Force realm re-import with updated redirect URIs
- Verify test users, client config, and token claims
- Confirm OAuth login flow uses consistent hostnames

Part of Phase 7: Login Fix
```

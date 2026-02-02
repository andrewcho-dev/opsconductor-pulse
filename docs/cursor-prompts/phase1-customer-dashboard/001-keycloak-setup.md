# Task 001: Keycloak Docker Setup

## Context

OpsConductor-Pulse needs authentication via Keycloak for customer and operator access. Currently there is no authentication — the UI is open.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 1: Unified Authentication Model)
- `compose/docker-compose.yml` (current services)

## Task

### 1.1 Modify `compose/docker-compose.yml`

Add Keycloak service after the existing services:

**Service configuration**:
- Image: `quay.io/keycloak/keycloak:24.0`
- Container name: `pulse-keycloak`
- Port mapping: `8180:8080`
- Environment variables:
  - `KEYCLOAK_ADMIN`: `admin`
  - `KEYCLOAK_ADMIN_PASSWORD`: `admin_dev`
  - `KC_DB`: `postgres`
  - `KC_DB_URL`: `jdbc:postgresql://iot-postgres:5432/iotcloud`
  - `KC_DB_USERNAME`: `iot`
  - `KC_DB_PASSWORD`: `iot_dev`
  - `KC_HOSTNAME_STRICT`: `false`
  - `KC_HTTP_ENABLED`: `true`
- Command: `start-dev --import-realm`
- Volume: `./keycloak/realm-pulse.json:/opt/keycloak/data/import/realm-pulse.json`
- Depends on: `postgres` (condition: service_healthy)
- Restart: `unless-stopped`

### 1.2 Create `compose/keycloak/realm-pulse.json`

Create the Keycloak realm export file with:

**Realm settings**:
- Realm name: `pulse`
- Enabled: true
- Login theme: default
- Access token lifespan: 300 (5 minutes)
- Refresh token lifespan: 1800 (30 minutes)

**Clients**:

1. Client `pulse-ui`:
   - Client ID: `pulse-ui`
   - Public client: true
   - Direct access grants: true
   - Standard flow: true
   - PKCE required: true (S256)
   - Valid redirect URIs: `http://localhost:8080/*`, `http://127.0.0.1:8080/*`
   - Web origins: `http://localhost:8080`, `http://127.0.0.1:8080`

2. Client `pulse-api`:
   - Client ID: `pulse-api`
   - Public client: false
   - Service accounts: true
   - Client secret: `pulse-api-secret-dev`

**Protocol Mappers** (add to both clients):

1. Mapper `tenant_id`:
   - Protocol: openid-connect
   - Mapper type: User Attribute
   - User attribute: `tenant_id`
   - Token claim name: `tenant_id`
   - Claim JSON type: String
   - Add to ID token: true
   - Add to access token: true
   - Add to userinfo: true

2. Mapper `role`:
   - Protocol: openid-connect
   - Mapper type: User Attribute
   - User attribute: `role`
   - Token claim name: `role`
   - Claim JSON type: String
   - Add to ID token: true
   - Add to access token: true
   - Add to userinfo: true

**Test Users**:

1. User `customer1`:
   - Username: `customer1`
   - Email: `customer1@tenant-a.example.com`
   - Enabled: true
   - Credentials: password `test123`, temporary: false
   - Attributes:
     - `tenant_id`: `tenant-a`
     - `role`: `customer_admin`

2. User `customer2`:
   - Username: `customer2`
   - Email: `customer2@tenant-b.example.com`
   - Enabled: true
   - Credentials: password `test123`, temporary: false
   - Attributes:
     - `tenant_id`: `tenant-b`
     - `role`: `customer_viewer`

3. User `operator1`:
   - Username: `operator1`
   - Email: `operator1@opsconductor.io`
   - Enabled: true
   - Credentials: password `test123`, temporary: false
   - Attributes:
     - `tenant_id`: (empty/null)
     - `role`: `operator`

4. User `operator_admin`:
   - Username: `operator_admin`
   - Email: `admin@opsconductor.io`
   - Enabled: true
   - Credentials: password `test123`, temporary: false
   - Attributes:
     - `tenant_id`: (empty/null)
     - `role`: `operator_admin`

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `compose/docker-compose.yml` |
| CREATE | `compose/keycloak/realm-pulse.json` |

## Acceptance Criteria

- [ ] `docker-compose up keycloak` starts without errors
- [ ] Keycloak admin console accessible at http://localhost:8180
- [ ] Can login to admin console with admin/admin_dev
- [ ] `pulse` realm exists with 2 clients and 4 users
- [ ] JWKS endpoint responds: http://localhost:8180/realms/pulse/protocol/openid-connect/certs
- [ ] Can obtain token for customer1:
  ```bash
  curl -X POST http://localhost:8180/realms/pulse/protocol/openid-connect/token \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" \
    -d "grant_type=password"
  ```
- [ ] Token contains `tenant_id` and `role` claims

## Commit

```
Add Keycloak to Docker Compose with realm config

- Keycloak 24.0 with PostgreSQL backend
- pulse realm with tenant_id and role mappers
- Test users: customer1 (tenant-a), customer2 (tenant-b), operator1, operator_admin
- JWKS endpoint for JWT validation

Part of Phase 1: Customer Read-Only Dashboard
```

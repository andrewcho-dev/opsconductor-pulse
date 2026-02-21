# Fix JWT Issuer Mismatch in docker-compose.yml

Fix 401 Unauthorized errors caused by JWT issuer mismatch.

## Problem

The frontend gets JWTs from Keycloak at `https://192.168.10.53/realms/pulse` but the backend (`services/ui_iot/middleware/auth.py:104`) expects issuer built from `KEYCLOAK_PUBLIC_URL` which defaults to `http://localhost:8180`.

This causes all `/api/v2/*` calls to return 401 "Invalid token claims".

## Fix

In `compose/docker-compose.yml`, update the ui_iot service environment to set `KEYCLOAK_PUBLIC_URL` to use the actual external Keycloak URL.

Change line ~235 from:

```yaml
KEYCLOAK_PUBLIC_URL: "${KEYCLOAK_URL:-http://localhost:8180}"
```

To:

```yaml
KEYCLOAK_PUBLIC_URL: "${KEYCLOAK_URL:-https://192.168.10.53}"
```

This ensures the issuer validation at `auth.py:113` matches the token's `iss` claim.

## Scope

- Only modify `compose/docker-compose.yml`
- Do not change any other files

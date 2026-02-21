# Phase 35: JWT Issuer Mismatch Fix

## Problem Summary

All `/api/v2/*` API calls return 401 Unauthorized after successful Keycloak login.

## Root Cause

JWT issuer validation mismatch:
- **Token issuer**: `https://192.168.10.53/realms/pulse`
- **Backend expects**: `http://localhost:8180/realms/pulse` (built from `KEYCLOAK_PUBLIC_URL` env var)

The backend at `services/ui_iot/middleware/auth.py:104` builds the expected issuer from environment variables, but the default value doesn't match the actual Keycloak URL.

## Execution Order

1. `001-fix-keycloak-url.md` - Update docker-compose.yml

## Files Modified

- `compose/docker-compose.yml`

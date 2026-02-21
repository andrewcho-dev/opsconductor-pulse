# Prompt 005 — Verify Phase 50

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

All must pass.

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

- [ ] `services/shared/jwks_cache.py` exists with JwksCache class
- [ ] `init_jwks_cache()` and `get_jwks_cache()` exported
- [ ] ui_iot pre-warms cache on startup
- [ ] Token verification uses cache
- [ ] `/healthz` includes keycloak check (non-fatal)
- [ ] `KEYCLOAK_JWKS_URI` in ui_iot `.env.example`
- [ ] 9 unit tests pass in `test_jwks_cache.py`

## Report

Output PASS / FAIL per criterion.

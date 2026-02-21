# Prompt 005 — Verify Phase 61

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: Import Check

```bash
cd services/ui_iot && python -c "from slowapi import Limiter; print('slowapi OK')"
```

## Step 3: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 4: Checklist

- [ ] `slowapi>=0.1.9` in ui_iot requirements.txt
- [ ] `RATE_LIMIT_CUSTOMER` in ui_iot .env.example
- [ ] `limiter` with `get_rate_limit_key` in app.py
- [ ] `SlowAPIMiddleware` added to app
- [ ] `@limiter.limit()` on GET /devices, GET /alerts, POST /apply
- [ ] 429 response returns JSON (not HTML)
- [ ] `Retry-After` header in 429 response
- [ ] Health/metrics/operator endpoints NOT rate-limited
- [ ] 6 unit tests in test_rate_limiting.py

## Report

Output PASS / FAIL per criterion.

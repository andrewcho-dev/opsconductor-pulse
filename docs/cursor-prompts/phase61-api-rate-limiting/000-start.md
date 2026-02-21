# Phase 61: API Rate Limiting (ui_iot)

## What Exists

- `services/ingest_iot/ingest.py` — already has per-device token bucket rate limiting (5 RPS default, 20 burst) via `shared.ingest_core.TokenBucket`
- `services/ui_iot/app.py` — no rate limiting; has CSRF middleware and RequestId middleware
- `slowapi` / `limits` — NOT currently installed

## What This Phase Adds

Per-tenant rate limiting on the `ui_iot` REST API:
1. **`slowapi` library** added to ui_iot requirements
2. **Rate limit middleware** on `services/ui_iot/app.py` — uses `slowapi` with tenant_id as the key
3. **Configurable limits** via environment variables:
   - `RATE_LIMIT_CUSTOMER` — default `"100/minute"` (customer API calls)
   - `RATE_LIMIT_INGEST` — default `"200/minute"` (ingest API endpoints if any)
4. **`X-RateLimit-*` response headers** — `slowapi` adds these automatically
5. **429 responses** return JSON `{"detail": "Rate limit exceeded"}` (not HTML)
6. **Operator and health endpoints exempt** — only customer routes rate-limited

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Add slowapi, configure limiter in app.py |
| 002 | Apply rate limits to customer router |
| 003 | 429 error handler + JSON response |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `services/ui_iot/requirements.txt` — prompt 001
- `services/ui_iot/app.py` — prompts 001, 003
- `services/ui_iot/routes/customer.py` — prompt 002
- `services/ui_iot/.env.example` — prompt 001

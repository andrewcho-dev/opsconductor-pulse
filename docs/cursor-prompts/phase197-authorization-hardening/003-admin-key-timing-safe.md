# Task 3: Fix Admin Key Comparison and Add Rate Limiting

## Context

`services/provision_api/app.py:177-180` compares the admin key using Python's `!=` operator. This is vulnerable to timing attacks — an attacker can measure response time differences to deduce the key character by character.

Additionally, there is no rate limiting on admin endpoints, so brute force attacks are unrestricted.

## Actions

1. Read `services/provision_api/app.py` in full.

2. Find the `require_admin()` dependency function. Change the comparison to use `secrets.compare_digest()`:

```python
import secrets

def require_admin(x_admin_key: str | None = Header(default=None)):
    if x_admin_key is None:
        log_event(logger, "provision attempt failed", level="WARNING", reason="missing_admin_key")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Constant-time comparison prevents timing attacks
    if not secrets.compare_digest(x_admin_key.encode(), ADMIN_KEY.encode()):
        log_event(logger, "provision attempt failed", level="WARNING", reason="invalid_admin_key")
        raise HTTPException(status_code=401, detail="Unauthorized")
```

3. Add a startup validation that `ADMIN_KEY` is non-empty and has minimum length:
```python
if len(ADMIN_KEY) < 32:
    raise RuntimeError("ADMIN_KEY must be at least 32 characters. Generate with: openssl rand -hex 32")
```

4. Add rate limiting to admin endpoints. Look at how other endpoints in the codebase implement rate limiting (likely using `slowapi` or a similar pattern). Apply the same limiter to all routes that use the `require_admin` dependency:
```python
# Example with slowapi
@limiter.limit("10/minute")
@app.post("/provision/device")
async def provision_device(request: Request, ...):
    ...
```
Apply a limit of 10 requests per minute per IP for admin endpoints.

5. Do not change any provisioning logic.

## Verification

```bash
grep -n 'compare_digest' services/provision_api/app.py
# Must show timing-safe comparison

grep -n 'limiter\|rate_limit\|@limit' services/provision_api/app.py
# Must show rate limiting on admin routes
```

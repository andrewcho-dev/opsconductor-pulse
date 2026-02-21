# Prompt 003 — 429 Error Handler (JSON Response)

Read `services/ui_iot/app.py`.

## Add 429 Handler

By default, `slowapi` returns an HTML 429 response. Override it to return JSON:

```python
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
        headers={"Retry-After": str(exc.retry_after) if hasattr(exc, "retry_after") else "60"},
    )
```

Also ensure `slowapi` middleware is added to the app:

```python
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)
```

## Acceptance Criteria

- [ ] 429 responses return JSON `{"detail": "Rate limit exceeded. Please slow down."}`
- [ ] `Retry-After` header present in 429 response
- [ ] SlowAPIMiddleware added to app
- [ ] `pytest -m unit -v` passes

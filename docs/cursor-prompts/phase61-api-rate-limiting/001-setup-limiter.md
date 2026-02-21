# Prompt 001 — Add slowapi + Configure Limiter

## Add to `services/ui_iot/requirements.txt`

```
slowapi>=0.1.9
```

## Add to `services/ui_iot/.env.example`

```
# Rate limiting (slowapi)
RATE_LIMIT_CUSTOMER=100/minute
```

## Update `services/ui_iot/app.py`

Read the file fully first.

Add limiter setup after imports:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def get_rate_limit_key(request: Request) -> str:
    """Use tenant_id as rate limit key; fall back to IP if no tenant context."""
    # Try to get tenant_id from request state (set by auth middleware)
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return tenant_id
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
```

Add the 429 error handler to `app` (see prompt 003).

## Acceptance Criteria

- [ ] `slowapi>=0.1.9` in ui_iot requirements.txt
- [ ] `RATE_LIMIT_CUSTOMER` in .env.example
- [ ] `limiter` created with `get_rate_limit_key` in app.py
- [ ] `app.state.limiter` set

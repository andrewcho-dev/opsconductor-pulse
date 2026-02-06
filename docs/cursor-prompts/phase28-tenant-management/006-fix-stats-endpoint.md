# Phase 28.6: Fix Missing Stats Endpoint

## Problem

`/operator/tenants/stats/summary` returns 404.

## Check

Look at `services/ui_iot/routes/operator.py` and verify:

1. The endpoint exists:
```python
@router.get("/tenants/stats/summary")
async def get_all_tenants_stats(request: Request):
```

2. It's defined BEFORE the `@router.get("/tenants/{tenant_id}")` route (order matters in FastAPI — specific routes must come before parameterized routes)

## Fix

Move the `/tenants/stats/summary` endpoint ABOVE `/tenants/{tenant_id}`:

```python
# This must come FIRST (specific route)
@router.get("/tenants/stats/summary")
async def get_all_tenants_stats(request: Request):
    ...

# This must come AFTER (parameterized route catches everything)
@router.get("/tenants/{tenant_id}")
async def get_tenant(request: Request, tenant_id: str):
    ...
```

If the endpoint doesn't exist at all, add it from `003-tenant-stats-api.md`.

## Restart

```bash
docker compose restart ui
```

Then refresh `/operator/tenants` page.

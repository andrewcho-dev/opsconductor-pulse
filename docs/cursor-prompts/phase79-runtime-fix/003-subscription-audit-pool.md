# Phase 79d — Fix pool NameError in get_subscription_audit

## Problem

`GET /customer/subscription/audit` returns 500 because `get_subscription_audit`
uses `p = pool` in the body but has no `pool` parameter in its signature.

## Fix

In `services/ui_iot/routes/customer.py`, find the function at line ~1562:

```python
@router.get("/subscription/audit")
async def get_subscription_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
```

Change the signature to:

```python
@router.get("/subscription/audit")
async def get_subscription_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
```

Do NOT change the function body.

## Verify

```bash
docker compose restart ui_iot
curl -s -o /dev/null -w "%{http_code}" \
  "https://192.168.10.53/customer/subscription/audit?limit=20" \
  -H "Authorization: Bearer <tenant-admin-token>"
```

Should return 200.

## Commit and push

```bash
git add services/ui_iot/routes/customer.py
git commit -m "Fix pool dependency missing from get_subscription_audit signature"
git push origin main
git log --oneline -3
```

# Task 003 — Fix Legacy Subscriptions Route + Frontend Callers

## Problem

`GET /api/v1/customer/subscriptions` and `GET /api/v1/customer/subscriptions/{id}` still query the dropped `subscriptions` table, causing 500 errors. Three frontend files call these endpoints.

## Files to Modify

1. `services/ui_iot/routes/customer.py` — rewrite both subscription endpoints to use `device_subscriptions`
2. `frontend/src/services/api/subscription.ts` — update types and query
3. `frontend/src/components/layout/SubscriptionBanner.tsx` — update response shape
4. `frontend/src/features/subscription/DeviceSelectionModal.tsx` — update or remove (old model concept)

## Part 1: Backend — `routes/customer.py`

### Rewrite `GET /subscriptions` (line 728)

Replace the entire `list_subscriptions` function. Query `device_subscriptions` joined with `device_plans`:

```python
@router.get("/subscriptions")
async def list_subscriptions(
    include_expired: bool = Query(False),
    pool=Depends(get_db_pool),
):
    """List all device subscriptions for the tenant."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        status_filter = "" if include_expired else "AND ds.status NOT IN ('EXPIRED', 'CANCELLED')"
        rows = await conn.fetch(
            f"""
            SELECT ds.subscription_id, ds.device_id, ds.plan_id, ds.status,
                   ds.term_start, ds.term_end, ds.grace_end,
                   ds.stripe_subscription_id, ds.created_at,
                   dp.name AS plan_name, dp.monthly_price_cents
            FROM device_subscriptions ds
            LEFT JOIN device_plans dp ON dp.plan_id = ds.plan_id
            WHERE ds.tenant_id = $1 {status_filter}
            ORDER BY ds.device_id
            """,
            tenant_id,
        )

    subscriptions = [
        {
            "subscription_id": r["subscription_id"],
            "device_id": r["device_id"],
            "plan_id": r["plan_id"],
            "plan_name": r["plan_name"],
            "status": r["status"],
            "term_start": r["term_start"].isoformat() if r["term_start"] else None,
            "term_end": r["term_end"].isoformat() if r["term_end"] else None,
            "monthly_price_cents": r["monthly_price_cents"],
        }
        for r in rows
    ]

    active_count = sum(1 for s in subscriptions if s["status"] in ("ACTIVE", "TRIAL"))

    return {
        "subscriptions": subscriptions,
        "summary": {
            "total_subscriptions": len(subscriptions),
            "active_subscriptions": active_count,
        },
    }
```

### Rewrite `GET /subscriptions/{subscription_id}` (line 813)

Replace the entire `get_subscription_detail` function. In the new model, each subscription covers exactly 1 device:

```python
@router.get("/subscriptions/{subscription_id}")
async def get_subscription_detail(subscription_id: str, pool=Depends(get_db_pool)):
    """Get details of a specific device subscription."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT ds.*, dp.name AS plan_name, dp.monthly_price_cents,
                   dp.limits AS plan_limits, dp.features AS plan_features
            FROM device_subscriptions ds
            LEFT JOIN device_plans dp ON dp.plan_id = ds.plan_id
            WHERE ds.subscription_id = $1 AND ds.tenant_id = $2
            """,
            subscription_id,
            tenant_id,
        )

        if not row:
            raise HTTPException(404, "Subscription not found")

        days_until_expiry = None
        if row["term_end"]:
            delta = row["term_end"] - datetime.now(timezone.utc)
            days_until_expiry = max(0, delta.days)

        return {
            "subscription_id": row["subscription_id"],
            "device_id": row["device_id"],
            "plan_id": row["plan_id"],
            "plan_name": row["plan_name"],
            "status": row["status"],
            "term_start": row["term_start"].isoformat() if row["term_start"] else None,
            "term_end": row["term_end"].isoformat() if row["term_end"] else None,
            "days_until_expiry": days_until_expiry,
            "monthly_price_cents": row["monthly_price_cents"],
            "plan_limits": row["plan_limits"],
            "plan_features": row["plan_features"],
        }
```

## Part 2: Frontend — `subscription.ts`

Rewrite `getSubscription()` for the new response shape:

```typescript
export interface SubscriptionStatus {
  total_subscriptions: number;
  active_subscriptions: number;
  worst_status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED" | "CANCELLED";
  earliest_expiry_days: number | null;
}

export async function getSubscription(): Promise<SubscriptionStatus> {
  const response = await apiGet<{
    subscriptions: {
      subscription_id: string;
      device_id: string;
      plan_id: string;
      status: string;
      term_end: string | null;
    }[];
    summary: {
      total_subscriptions: number;
      active_subscriptions: number;
    };
  }>("/api/v1/customer/subscriptions");

  const statuses = response.subscriptions.map((s) => s.status);
  let worst_status: SubscriptionStatus["worst_status"] = "ACTIVE";
  if (statuses.includes("SUSPENDED")) worst_status = "SUSPENDED";
  else if (statuses.includes("GRACE")) worst_status = "GRACE";
  else if (statuses.includes("TRIAL") && !statuses.includes("ACTIVE")) worst_status = "TRIAL";

  const activeTerms = response.subscriptions
    .filter((s) => s.status === "ACTIVE" && s.term_end)
    .map((s) => new Date(s.term_end as string));
  const earliestExpiry = activeTerms.length
    ? new Date(Math.min(...activeTerms.map((d) => d.getTime())))
    : null;
  const earliest_expiry_days = earliestExpiry
    ? Math.max(0, Math.ceil((earliestExpiry.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : null;

  return {
    total_subscriptions: response.summary.total_subscriptions,
    active_subscriptions: response.summary.active_subscriptions,
    worst_status,
    earliest_expiry_days,
  };
}
```

Keep `getSubscriptionAudit` unchanged if the audit endpoint still works.

## Part 3: Frontend — `SubscriptionBanner.tsx`

Update the response type. The banner cares about subscription status (SUSPENDED, GRACE, expiring). The new response has the same `subscriptions[].status` and `subscriptions[].term_end` fields, so the banner logic mostly works. Just remove references to the old `summary` shape:

1. Change the `SubscriptionsResponse` interface:

```typescript
interface SubscriptionsResponse {
  subscriptions: {
    subscription_id: string;
    device_id: string;
    status: string;
    term_end: string | null;
  }[];
  summary: {
    total_subscriptions: number;
    active_subscriptions: number;
  };
}
```

2. The rest of the component logic (checking for SUSPENDED, GRACE, expiring) already works correctly — it only reads `subscription_id`, `status`, and `term_end` from each subscription.

## Part 4: Frontend — `DeviceSelectionModal.tsx`

This modal was designed for the old model where downgrading a subscription meant deactivating N devices from a pool. In the new per-device model, each subscription covers exactly 1 device — there's no "select which devices to deactivate" flow.

**Option A (recommended):** Leave the file as-is but ensure nothing renders it. Search for imports of `DeviceSelectionModal` — if `RenewalPage.tsx` was rewritten in Phase 156 Task 005 and no longer uses it, the modal is dead code.

**Option B:** Delete the file if unused.

Check with:
```bash
grep -r "DeviceSelectionModal" frontend/src/ --include="*.tsx" --include="*.ts" | grep -v "DeviceSelectionModal.tsx"
```

If no results, delete `frontend/src/features/subscription/DeviceSelectionModal.tsx`.

## Verification

```bash
# Backend
cd services/ui_iot && python3 -m compileall routes/customer.py -q

# Frontend
cd frontend && npx tsc --noEmit && npm run build

# Live test
curl -s -H "Authorization: Bearer $TOKEN" https://pulse.enabledconsultants.com/api/v1/customer/subscriptions | python3 -m json.tool
# Should return device_subscriptions data, not 500
```

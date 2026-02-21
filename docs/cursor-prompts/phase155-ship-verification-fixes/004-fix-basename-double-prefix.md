# Task 004 — Fix /app/app/ Double Prefix in Navigation Links

## Problem

The React Router is configured with `basename: "/app"` (`router.tsx:173`). All `<Link to="...">` and `navigate("...")` paths are relative to this basename. Several subscription-related files use `"/app/subscription/..."` which produces `"/app/app/subscription/..."` in the browser.

## Files to Modify

1. `frontend/src/features/subscription/SubscriptionPage.tsx` — line 160
2. `frontend/src/features/subscription/RenewalPage.tsx` — line 182
3. `frontend/src/components/layout/SubscriptionBanner.tsx` — lines 91, 127

## Fix

Remove the `/app` prefix from all 4 occurrences:

### SubscriptionPage.tsx line 160

```
Change: <Link to="/app/subscription/renew">
To:     <Link to="/subscription/renew">
```

### RenewalPage.tsx line 182

```
Change: navigate("/app/subscription")
To:     navigate("/subscription")
```

### SubscriptionBanner.tsx line 91

```
Change: navigate("/app/subscription/renew")
To:     navigate("/subscription/renew")
```

### SubscriptionBanner.tsx line 127

```
Change: navigate("/app/subscription/renew")
To:     navigate("/subscription/renew")
```

## Also check `window.location` references

In `RenewalPage.tsx`, the Stripe success/cancel URLs use `window.location.origin` which is correct — those are full external URLs, not React Router paths. Leave them as-is:
```tsx
success_url: `${window.location.origin}/app/subscription?success=true`,   // correct — full URL
cancel_url: `${window.location.origin}/app/subscription/renew`,           // correct — full URL
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Then click "Change Tier" on the subscription page — should navigate to `/app/subscription/renew` (not `/app/app/subscription/renew`).

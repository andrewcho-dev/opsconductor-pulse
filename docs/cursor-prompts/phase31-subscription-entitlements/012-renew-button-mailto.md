# 012: Renew Now Button - Mailto (Temporary)

## Task

Update the "Renew Now" and "Contact Support" buttons in the subscription banner to open mailto links. This is a temporary solution until the full renewal workflow is implemented.

## File to Modify

`frontend/src/components/layout/SubscriptionBanner.tsx`

## Changes

### 1. Add tenant_id to the query result usage

The `getSubscription` function already returns `tenant_id`. Update the destructuring to include it:

```tsx
const { status, days_until_expiry, grace_end, tenant_id } =
  subscription as SubscriptionStatus & { tenant_id: string };
```

### 2. Update SUSPENDED/EXPIRED "Contact Support" button

```tsx
<Button
  variant="outline"
  size="sm"
  onClick={() => {
    window.location.href = `mailto:support@opsconductor.com?subject=${encodeURIComponent(
      `Subscription Support - ${tenant_id}`
    )}&body=${encodeURIComponent(
      `Tenant ID: ${tenant_id}\nStatus: ${status}\n\nPlease describe your issue:\n`
    )}`;
  }}
>
  Contact Support
</Button>
```

### 3. Update GRACE "Renew Now" button

```tsx
<Button
  variant="outline"
  size="sm"
  className="border-orange-500 text-orange-700 hover:bg-orange-100"
  onClick={() => {
    window.location.href = `mailto:sales@opsconductor.com?subject=${encodeURIComponent(
      `Subscription Renewal - ${tenant_id}`
    )}&body=${encodeURIComponent(
      `Tenant ID: ${tenant_id}\nCurrent Status: ${status}\nGrace Period Ends: ${grace_end || 'N/A'}\n\nI would like to renew my subscription.\n`
    )}`;
  }}
>
  Renew Now
</Button>
```

### 4. Update ACTIVE (expiring soon) "Renew Now" button

```tsx
<Button
  variant="outline"
  size="sm"
  className="border-yellow-500 text-yellow-700 hover:bg-yellow-100"
  onClick={() => {
    window.location.href = `mailto:sales@opsconductor.com?subject=${encodeURIComponent(
      `Subscription Renewal - ${tenant_id}`
    )}&body=${encodeURIComponent(
      `Tenant ID: ${tenant_id}\nDays Until Expiry: ${days_until_expiry}\n\nI would like to renew my subscription.\n`
    )}`;
  }}
>
  Renew Now
</Button>
```

## Note

This is a temporary solution. The full renewal workflow (Phase 31B) will replace these with proper renewal request pages.

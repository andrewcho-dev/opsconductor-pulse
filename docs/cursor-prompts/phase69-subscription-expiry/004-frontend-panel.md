# Prompt 004 — Frontend: Notification Status Panel

Read `frontend/src/features/operator/TenantDetailPage.tsx` and `frontend/src/services/api/operator.ts`.

## Add API Function

In `frontend/src/services/api/operator.ts`:

```typescript
export interface ExpiryNotification {
  id: string | number;
  tenant_id: string;
  notification_type: string;
  scheduled_at: string;
  sent_at: string | null;
  channel: string | null;
  status: string;
  error: string | null;
}

export async function fetchExpiryNotifications(params?: {
  status?: string; tenant_id?: string; limit?: number;
}): Promise<{ notifications: ExpiryNotification[]; total: number }> {
  const qs = new URLSearchParams(params as any).toString();
  return apiFetch(`/operator/subscriptions/expiring-notifications${qs ? '?' + qs : ''}`);
}
```

## Add Panel to TenantDetailPage

In `TenantDetailPage.tsx`, add a new section below subscriptions:

**"Expiry Notifications"** — table showing:
- Notification Type
- Scheduled At
- Status (badge: SENT=green, PENDING=yellow, FAILED=red)
- Channel (email/webhook/log)
- Sent At
- Error (if FAILED, show error text)

Fetches `fetchExpiryNotifications({ tenant_id: tenantId })`.

## Acceptance Criteria

- [ ] `fetchExpiryNotifications` in operator.ts
- [ ] Notification panel in TenantDetailPage
- [ ] Status badges colored correctly
- [ ] `npm run build` passes

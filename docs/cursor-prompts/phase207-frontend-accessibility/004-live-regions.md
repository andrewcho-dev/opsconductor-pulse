Screen readers need to be told when dynamic content changes — like when a new alert arrives, when a device goes offline, or when a form submission succeeds or fails. Add `aria-live` regions for these.

First check if the toast/notification system (Sonner) is accessible — it usually handles its own announcements. Search:

```bash
grep -rn 'toast\|Toaster\|Sonner' frontend/src/ --include="*.tsx" | head -10
```

If Sonner is used for success/error notifications, it likely handles `aria-live` internally. Confirm this is the case.

For the alert inbox specifically (`frontend/src/features/alerts/`): when new alerts arrive via WebSocket, screen readers don't know unless there's a live region. Add one:

```tsx
// In the alerts page or alert store, add a visually-hidden live region
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  {newAlertCount > 0 ? `${newAlertCount} new alert${newAlertCount > 1 ? 's' : ''}` : ''}
</div>
```

Use `aria-live="polite"` for non-urgent updates (new alerts, status changes). Use `aria-live="assertive"` only for critical errors that require immediate attention.

Also add a live region for the device connection status indicator — when a device goes from ONLINE to OFFLINE, that should be announced.

Don't overdo it — too many live regions are as bad as none. Focus on: new alerts arriving, form submission results, and critical status changes.

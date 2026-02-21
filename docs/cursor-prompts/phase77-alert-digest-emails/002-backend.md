# Prompt 002 — Backend: Digest Settings + Worker Job

### Part A: Settings endpoints in customer.py

Read `services/ui_iot/routes/customer.py`.

Add:

**GET /customer/alert-digest-settings**  
Returns current tenant's digest settings (or defaults if not set).

**PUT /customer/alert-digest-settings**  
Body: `{ "frequency": "daily" | "weekly" | "disabled", "email": "user@example.com" }`  
Upsert into alert_digest_settings.

### Part B: Digest job in subscription_worker

Read `services/subscription_worker/worker.py` (or main file) to understand the job loop pattern.

Add `send_alert_digest()` async function:

```python
async def send_alert_digest(pool):
    """
    For each tenant in alert_digest_settings where frequency != 'disabled':
    - Check if it's time to send (daily: last_sent_at < now() - interval '1 day',
      weekly: last_sent_at < now() - interval '7 days', or never sent)
    - Query fleet_alert for OPEN alerts (count by severity)
    - If count > 0, render and send email using aiosmtplib (same pattern as subscription expiry emails)
    - Update last_sent_at
    """
```

Email subject: `"[OpsConductor] Alert Digest — {open_count} open alerts"`

Email body (plain text):
```
Alert Digest for {tenant_id}
Generated: {now}

Open Alerts Summary:
  CRITICAL: {n}
  HIGH: {n}
  MEDIUM: {n}
  LOW: {n}

Total open alerts: {total}

Log in to OpsConductor to view and manage alerts.
```

Call `send_alert_digest(pool)` in the worker's main loop at a reasonable interval (e.g., every 3600 seconds).

## Acceptance Criteria
- [ ] GET /customer/alert-digest-settings returns settings
- [ ] PUT upserts settings
- [ ] send_alert_digest() in subscription_worker
- [ ] Scheduled in worker loop
- [ ] aiosmtplib used for sending

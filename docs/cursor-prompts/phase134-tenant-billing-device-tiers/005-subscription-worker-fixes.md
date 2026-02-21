# 005 -- Fix Subscription Worker: SMTP, Tenant Email Targeting, Renewal

## Context

The `subscription_worker` service (`services/subscription_worker/worker.py`) already has a solid expiry notification pipeline:
- Schedules renewal notifications at 90, 60, 30, 14, 7, 1 days before expiry
- Transitions ACTIVE → GRACE (14-day grace period) → SUSPENDED
- Sends notification emails with HTML templates
- Reconciles device counts nightly

**But it's broken in production:**
1. SMTP env vars are NOT in `compose/docker-compose.yml` for the subscription-worker service → emails silently skipped
2. `send_expiry_notification_email()` sends to `NOTIFICATION_EMAIL_TO` env var (a single global address) instead of the tenant's billing/contact email
3. No integration with Stripe auto-renewal

## Task

### Step 1: Add SMTP Environment Variables to Docker Compose

In `compose/docker-compose.yml`, find the `subscription-worker` service (around line 298-318). Add SMTP env vars to its environment section:

```yaml
subscription-worker:
  # ... existing config ...
  environment:
    DATABASE_URL: "postgresql://iot:${PG_PASS}@iot-pgbouncer:5432/iotcloud"
    WORKER_INTERVAL_SECONDS: "3600"
    # Add these:
    SMTP_HOST: ${SMTP_HOST:-}
    SMTP_PORT: ${SMTP_PORT:-587}
    SMTP_USER: ${SMTP_USER:-}
    SMTP_PASSWORD: ${SMTP_PASSWORD:-}
    SMTP_FROM: ${SMTP_FROM:-noreply@pulse.local}
    SMTP_TLS: ${SMTP_TLS:-true}
```

### Step 2: Fix Email Targeting — Send to Tenant's Billing Email

In `services/subscription_worker/worker.py`, update `send_expiry_notification_email()` (around line 168):

**Current code** (broken — sends to global env var):
```python
to_address = os.environ.get("NOTIFICATION_EMAIL_TO")
if not to_address:
    return False
```

**Replace with** (sends to tenant's billing_email or contact_email):
```python
# Remove the NOTIFICATION_EMAIL_TO check. Instead, accept the tenant email as a parameter.
```

**Refactor the function signature** to accept the recipient email:
```python
async def send_expiry_notification_email(
    notification: dict,
    subscription: dict,
    tenant: dict,
) -> bool:
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        return False

    # Use tenant's billing_email, falling back to contact_email
    to_address = tenant.get("billing_email") or tenant.get("contact_email")
    if not to_address:
        logger.warning("No email address for tenant %s", tenant.get("tenant_id"))
        return False

    # ... rest of the function unchanged ...
```

**Update `process_pending_notifications()`** (around line 92) to fetch the tenant's email addresses. Change the SQL query to include billing_email and contact_email:

```python
pending = await conn.fetch(
    """
    SELECT n.id, n.tenant_id, n.notification_type, t.name as tenant_name,
           t.billing_email, t.contact_email,
           s.subscription_id, s.term_end, s.grace_end, s.status,
           s.device_limit, s.active_device_count
    FROM subscription_notifications n
    JOIN tenants t ON t.tenant_id = n.tenant_id
    JOIN subscriptions s ON s.tenant_id = n.tenant_id AND s.subscription_type = 'MAIN'
    WHERE n.status = 'PENDING'
      AND n.scheduled_at <= now()
    ORDER BY n.scheduled_at
    LIMIT 100
    """
)
```

And update the `send_expiry_notification_email` call to pass the full tenant dict:
```python
email_sent = await send_expiry_notification_email(
    notification=dict(row),
    subscription=dict(row),
    tenant={
        "tenant_id": row["tenant_id"],
        "name": row["tenant_name"],
        "billing_email": row["billing_email"],
        "contact_email": row["contact_email"],
    },
)
```

### Step 3: Handle Stripe-Managed Subscription Renewals

When Stripe auto-renews a subscription, it fires `invoice.paid` which the webhook handler (task 003) already handles by extending `term_end`. The subscription_worker doesn't need to do anything special for Stripe-managed subscriptions — the ACTIVE → GRACE transition only fires when `term_end` passes, and Stripe will have already extended `term_end` before that happens.

However, add a safety check to `process_grace_transitions()` to skip Stripe-managed subscriptions that are still active in Stripe:

In the ACTIVE → GRACE transition query (around line 341), add a condition to exclude Stripe-managed subscriptions where Stripe might still auto-renew:

```python
rows = await conn.fetch(
    """
    UPDATE subscriptions
    SET status = 'GRACE',
        grace_end = term_end + interval '14 days',
        updated_at = now()
    WHERE status = 'ACTIVE'
      AND term_end < $1
      AND stripe_subscription_id IS NULL  -- Only transition non-Stripe subs
    RETURNING subscription_id, tenant_id
    """,
    now,
)
```

**Rationale**: For Stripe-managed subscriptions, the status transitions are driven by Stripe webhooks (`subscription.updated` with status `past_due`/`canceled`), not by the worker checking `term_end`. Letting the worker also transition them creates a race condition.

For **non-Stripe** (operator-created) subscriptions, the worker continues to manage the ACTIVE → GRACE → SUSPENDED lifecycle as before.

### Step 4: Add Co-terminated Add-on Handling in Notifications

The notification scheduler currently only joins against `subscription_type = 'MAIN'`. Update it to also schedule notifications for ADDON subscriptions that have their own term_end (in case they're NOT co-terminated with a parent):

Actually, for co-terminated add-ons, the term_end matches the parent's — so the parent's notification covers both. No change needed here. The existing query already picks up the MAIN subscription's expiry, which is the co-termination date.

### Step 5: Clean Up Unused NOTIFICATION_EMAIL_TO References

Remove the `NOTIFICATION_EMAIL_TO` env var usage since emails now go to tenant-specific addresses. If the env var is referenced elsewhere in the worker, replace those references too. Search for `NOTIFICATION_EMAIL_TO` in the file and remove all references.

## Verify

```bash
# 1. Rebuild subscription-worker
docker compose -f compose/docker-compose.yml up -d --build subscription-worker

# 2. Check env vars are injected
docker compose -f compose/docker-compose.yml exec subscription-worker env | grep SMTP

# 3. Check logs for worker activity
docker compose -f compose/docker-compose.yml logs subscription-worker --tail=50

# 4. Manual test: run worker once
docker compose -f compose/docker-compose.yml exec subscription-worker \
  python -m worker --once

# 5. If there are subscriptions approaching expiry, check subscription_notifications table:
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT * FROM subscription_notifications ORDER BY scheduled_at DESC LIMIT 10"
```

## Commit

```
fix(phase134): wire SMTP to subscription-worker, send expiry emails to tenant

Add missing SMTP env vars to subscription-worker in docker-compose.
Change expiry notification email targeting from global NOTIFICATION_EMAIL_TO
to tenant's billing_email (falling back to contact_email). Skip Stripe-
managed subscriptions in worker's ACTIVE→GRACE transition to avoid
racing with Stripe webhook-driven status changes.
```

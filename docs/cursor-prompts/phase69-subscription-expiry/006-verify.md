# Prompt 006 — Verify Phase 69

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: Import Check

```bash
cd services/subscription_worker && python -c "import aiosmtplib; print('aiosmtplib OK')"
```

## Step 3: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 4: Checklist

- [ ] `aiosmtplib` in subscription_worker requirements.txt
- [ ] `email_templates.py` in subscription_worker with pre-expiry + grace templates
- [ ] `send_expiry_notification_email()` in worker.py
- [ ] Returns False gracefully when SMTP not configured
- [ ] GET /operator/subscriptions/expiring-notifications exists
- [ ] status/tenant_id filters work
- [ ] Notification panel in TenantDetailPage
- [ ] 7 unit tests in test_subscription_expiry.py

## Report

Output PASS / FAIL per criterion.

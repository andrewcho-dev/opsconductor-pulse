# Phase 205 Findings — Stripe Webhook Audit

Files reviewed:
- `services/ui_iot/routes/billing.py` (full)
- `services/ui_iot/services/stripe_service.py` (full)
- `services/subscription_worker/worker.py`, `email_templates.py`, `__init__.py`
- DB search for `stripe_events` table in `db/migrations/` and repo-wide references

## 1) Signature verification

- Verification is present.
- `billing.py` uses:
  - `payload = await request.body()`
  - `sig_header = request.headers.get("stripe-signature", "")`
  - `construct_webhook_event(payload, sig_header)` (which calls `stripe.Webhook.construct_event(...)` in `stripe_service.py`)
- Missing/invalid signature results in `HTTPException(400, "Invalid signature")`.

Assessment:
- No explicit bypass path found.
- Small hardening gap: missing signature header is treated as generic invalid signature instead of an explicit "missing header" branch.

## 2) Idempotency

- No idempotency check exists in webhook processing.
- No lookup/insert against a `stripe_events` store is performed.
- Repo search found no `stripe_events` table in migrations and no references outside telemetry SSE `Last-Event-ID` usage.

Assessment:
- Critical gap. Stripe re-delivery can cause duplicate state changes and duplicate side effects.

## 3) Event type checking

- Handler checks `event["type"]` and branches only for:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`
  - `invoice.paid`
- Other event types are ignored with debug log and return 200.

Assessment:
- Allowlist-like behavior is present (explicit branches + ignore default).

## 4) Data trust / Stripe re-fetch

- `checkout.session.completed`: re-fetches subscription via `retrieve_subscription(stripe_sub_id)` before deriving period/status.
- `invoice.paid`: re-fetches subscription via `retrieve_subscription(stripe_sub_id)` before extending term.
- `customer.subscription.updated`: trusts webhook payload `stripe_sub` directly (status/metadata/plan), does **not** re-fetch.
- `customer.subscription.deleted` / `invoice.payment_failed`: operate from event payload IDs only.

Assessment:
- Partial re-fetch pattern implemented; not consistent for all critical state transitions.

## 5) Sensitive data in logs

- No card PAN/CVC logging found.
- No payment method details logged.
- Event IDs/types and subscription IDs are logged.
- Potentially sensitive email logging found in Keycloak provisioning failures:
  - `logger.error("Failed to create Keycloak user %s: %s", admin_email, exc)`
  - `logger.info("Created Keycloak user %s for tenant %s", admin_email, tenant_id)`

Assessment:
- No card/payment leakage detected.
- Email logging should be minimized/redacted in security-hardening pass.

## 6) Error handling behavior

- Malformed/invalid signature: returns 400 (Stripe retries).
- Processing errors after signature verification are swallowed; handler logs exception and still returns `{"status":"ok"}` (200) to avoid retry storms.

Assessment:
- Intentional "ack on processing failure" behavior exists.
- Combined with missing idempotency, this increases risk of silently dropped webhook side effects (no retry) without durable recovery path.

## Summary

High-priority gaps to fix in subsequent tasks:
1. Add durable idempotency using `stripe_events` table (create migration if missing).
2. Strengthen signature-header validation path.
3. Normalize re-fetch strategy for authoritative subscription state on update transitions.
4. Reduce sensitive identifier logging (emails).

# Phase 205 — Stripe Webhook Security Audit

## Goal

Audit and harden the Stripe billing integration. The payment path was added in phase 133 and has never been reviewed for security. Webhook signature verification, idempotency, and subscription state transition correctness are all in scope.

## Current State (problem)

The Stripe integration exists in `services/ui_iot/routes/billing.py` and `services/subscription_worker/`. It has never been audited. Common Stripe integration vulnerabilities include: missing webhook signature verification, non-idempotent event handling, accepting events without checking their type, and trusting event data without re-fetching from Stripe API.

## Target State

- All inbound Stripe webhooks are verified using `stripe.Webhook.construct_event()` with the webhook secret.
- Webhook events are handled idempotently — re-delivery of the same event ID does not cause duplicate subscription changes.
- Subscription state transitions are validated — only expected event sequences are processed.
- No sensitive Stripe data is logged in plaintext.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-audit-webhook-handler.md` | Read and audit the webhook endpoint | — |
| 2 | `002-fix-signature-verification.md` | Ensure signature verification is correct and cannot be bypassed | Step 1 |
| 3 | `003-fix-idempotency.md` | Add idempotency check using `stripe_events` table | Step 1 |
| 4 | `004-fix-state-transitions.md` | Validate subscription state transitions | Step 1 |
| 5 | `005-update-documentation.md` | Update docs | Steps 1–4 |

## Verification

```bash
# Signature verification present
grep -n 'construct_event\|webhook_secret\|stripe_signature' services/ui_iot/routes/billing.py

# Idempotency check present
grep -n 'stripe_event\|event_id\|already.*processed' services/ui_iot/routes/billing.py services/subscription_worker/

# No plaintext card/payment data in logs
grep -rn 'logger.*card\|logger.*payment_method\|logger.*customer' services/ui_iot/routes/billing.py
```

## Documentation Impact

- `docs/features/billing.md` or `docs/operations/security.md` — Document webhook security model

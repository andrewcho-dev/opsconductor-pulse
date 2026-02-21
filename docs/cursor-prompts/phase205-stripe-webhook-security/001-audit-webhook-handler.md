Read these files in full before touching anything:

- `services/ui_iot/routes/billing.py`
- `services/subscription_worker/` (all .py files)
- The `stripe_events` table definition in `db/migrations/`

For the webhook handler, answer these questions and write your findings to `docs/cursor-prompts/phase205-stripe-webhook-security/001-findings.md`:

1. **Signature verification**: Is `stripe.Webhook.construct_event(payload, sig_header, webhook_secret)` called? If yes, can it be bypassed (e.g., is there a code path that skips it in dev mode or when a header is missing)? If no, that's a critical finding.

2. **Idempotency**: When a webhook event arrives, does the code check the `stripe_events` table to see if that `event.id` was already processed? Or does it process every delivery?

3. **Event type checking**: Does the handler check `event.type` before acting? Or does it try to process every event type regardless?

4. **Data trust**: After receiving a webhook event, does the code re-fetch the subscription/customer from Stripe API to confirm the state? Or does it trust the event payload data directly?

5. **Sensitive data in logs**: Are card details, payment method IDs, or customer emails being logged?

6. **Error handling**: What happens if Stripe sends a malformed event? Does the handler crash? Return 500? Return 200 (important — Stripe retries on non-200)?

Don't fix anything yet. Just document the findings.

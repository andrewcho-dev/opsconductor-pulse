Based on your findings from task 1, fix the webhook signature verification.

The correct Stripe webhook handler pattern is:

```python
@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception:
        logger.error("Stripe webhook parsing failed", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Process event...
    return {"status": "ok"}
```

Key rules:
- `construct_event` must be called on the raw bytes payload, NOT on a parsed JSON body. FastAPI's JSON body parsing will break the signature. Use `await request.body()` to get raw bytes.
- Never skip signature verification in any environment, including dev/test. If testing locally, use the Stripe CLI to forward events with valid signatures.
- `STRIPE_WEBHOOK_SECRET` must come from `require_env("STRIPE_WEBHOOK_SECRET")` — already done in phase 193, confirm it's in place.
- Return 400 on signature failure, not 200. Returning 200 on a bad signature tells Stripe "I got this" and it won't retry.

If signature verification was already correct, document that and move on.

# Task 003 -- Webhook HMAC Signing, Retry, and Delivery Audit

## Commit Message
```
feat: add HMAC-SHA256 webhook signing, retry with backoff, delivery audit
```

## Context

The current `send_webhook()` in `services/ui_iot/notifications/senders.py` has two issues:
1. The HMAC header is named `X-Signature-SHA256` instead of the standard `X-Signature-256` with `sha256=` prefix format.
2. There is no retry logic -- a single failure silently drops the notification.
3. There is no audit trail of delivery attempts.

This task fixes the signing format, adds exponential backoff retry, structured logging, and audit events.

## Step 1: Fix HMAC signature format in send_webhook()

In `services/ui_iot/notifications/senders.py`, the current code (lines 88-101):

```python
async def send_webhook(
    url: str,
    method: str,
    headers: dict,
    secret: str | None,
    alert: dict,
) -> None:
    body = json.dumps(alert).encode()
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        req_headers["X-Signature-SHA256"] = sig
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.request(method.upper(), url, content=body, headers=req_headers)
```

**Replace with:**

```python
import logging
import time

logger = logging.getLogger(__name__)

# Status codes that are retryable
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
# Status codes that should NOT be retried (client errors)
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}
# Retry delays in seconds (exponential backoff)
RETRY_DELAYS = [1, 5, 25]
MAX_ATTEMPTS = 3


def compute_webhook_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload.

    Returns signature in format: sha256=<hex_digest>
    """
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def send_webhook(
    url: str,
    method: str,
    headers: dict,
    secret: str | None,
    alert: dict,
    *,
    audit_logger=None,
    channel_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Send a webhook with HMAC-SHA256 signing and exponential backoff retry.

    Args:
        url: Target webhook URL.
        method: HTTP method (POST, PUT, etc.).
        headers: Additional headers to include.
        secret: HMAC secret for signing. If None, no signature header is added.
        alert: Alert payload to send as JSON body.
        audit_logger: Optional AuditLogger instance for recording delivery attempts.
        channel_id: Notification channel ID for audit trail.
        tenant_id: Tenant ID for audit trail.

    Returns:
        dict with keys: success (bool), status_code (int|None), attempts (int),
        duration_ms (int), error (str|None)
    """
    body = json.dumps(alert, default=str).encode()
    req_headers = {"Content-Type": "application/json", **(headers or {})}

    if secret:
        req_headers["X-Signature-256"] = compute_webhook_signature(body, secret)

    last_error: str | None = None
    last_status: int | None = None
    total_start = time.monotonic()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempt_start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method.upper(), url, content=body, headers=req_headers
                )

            attempt_duration_ms = int((time.monotonic() - attempt_start) * 1000)
            last_status = response.status_code

            logger.info(
                "webhook_delivery_attempt",
                extra={
                    "url": url,
                    "method": method.upper(),
                    "status_code": response.status_code,
                    "attempt": attempt,
                    "duration_ms": attempt_duration_ms,
                    "channel_id": channel_id,
                    "tenant_id": tenant_id,
                },
            )

            # Success: 2xx
            if 200 <= response.status_code < 300:
                total_duration_ms = int((time.monotonic() - total_start) * 1000)

                if audit_logger and tenant_id:
                    audit_logger.notification_delivered(
                        tenant_id,
                        channel_type="webhook",
                        channel_id=channel_id,
                        status="delivered",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "attempts": attempt,
                            "duration_ms": total_duration_ms,
                        },
                    )

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "attempts": attempt,
                    "duration_ms": total_duration_ms,
                    "error": None,
                }

            # Non-retryable client error
            if response.status_code in NON_RETRYABLE_STATUS_CODES:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(
                    "webhook_delivery_failed_non_retryable",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "channel_id": channel_id,
                        "tenant_id": tenant_id,
                        "response_body": response.text[:200],
                    },
                )
                break  # Do not retry

            # Retryable server error
            last_error = f"HTTP {response.status_code}"
            if attempt < MAX_ATTEMPTS:
                delay = RETRY_DELAYS[attempt - 1]
                logger.warning(
                    "webhook_delivery_retry",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "retry_delay_s": delay,
                        "channel_id": channel_id,
                    },
                )
                await asyncio.sleep(delay)
            # else: fall through to return failure

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            attempt_duration_ms = int((time.monotonic() - attempt_start) * 1000)
            last_error = f"{type(exc).__name__}: {str(exc)[:200]}"

            logger.warning(
                "webhook_delivery_connection_error",
                extra={
                    "url": url,
                    "attempt": attempt,
                    "duration_ms": attempt_duration_ms,
                    "error": last_error,
                    "channel_id": channel_id,
                    "tenant_id": tenant_id,
                },
            )

            if attempt < MAX_ATTEMPTS:
                delay = RETRY_DELAYS[attempt - 1]
                await asyncio.sleep(delay)

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            logger.exception(
                "webhook_delivery_unexpected_error",
                extra={
                    "url": url,
                    "attempt": attempt,
                    "channel_id": channel_id,
                    "tenant_id": tenant_id,
                },
            )
            break  # Do not retry unknown errors

    # All attempts exhausted or non-retryable error
    total_duration_ms = int((time.monotonic() - total_start) * 1000)

    logger.error(
        "webhook_delivery_failed",
        extra={
            "url": url,
            "attempts": attempt,
            "last_status": last_status,
            "last_error": last_error,
            "duration_ms": total_duration_ms,
            "channel_id": channel_id,
            "tenant_id": tenant_id,
        },
    )

    if audit_logger and tenant_id:
        audit_logger.notification_failed(
            tenant_id,
            channel_type="webhook",
            channel_id=channel_id,
            error=last_error or "Unknown error",
            details={
                "url": url,
                "last_status": last_status,
                "attempts": attempt,
                "duration_ms": total_duration_ms,
            },
        )

    return {
        "success": False,
        "status_code": last_status,
        "attempts": attempt,
        "duration_ms": total_duration_ms,
        "error": last_error,
    }
```

**Important:** Add `import asyncio` at the top of `senders.py`.

## Step 2: Add audit logger methods if they don't exist

Check `services/ui_iot/shared/audit.py` (or wherever AuditLogger is defined). If it does not have `notification_delivered` and `notification_failed` methods, add them:

```python
def notification_delivered(
    self,
    tenant_id: str,
    channel_type: str,
    channel_id: str | None = None,
    status: str = "delivered",
    details: dict | None = None,
):
    """Log a successful notification delivery."""
    self.log_event(
        tenant_id=tenant_id,
        event_type="NOTIFICATION_DELIVERED",
        category="notification",
        severity="info",
        entity_type="notification_channel",
        entity_id=channel_id,
        action="deliver",
        message=f"Notification delivered via {channel_type}",
        details=details,
    )

def notification_failed(
    self,
    tenant_id: str,
    channel_type: str,
    channel_id: str | None = None,
    error: str = "",
    details: dict | None = None,
):
    """Log a failed notification delivery."""
    self.log_event(
        tenant_id=tenant_id,
        event_type="NOTIFICATION_FAILED",
        category="notification",
        severity="warning",
        entity_type="notification_channel",
        entity_id=channel_id,
        action="deliver",
        message=f"Notification delivery failed via {channel_type}: {error}",
        details=details,
    )
```

If the AuditLogger uses a different `log_event` signature, adapt accordingly. The key is that the audit logger has a buffered/async write path that does not block the webhook delivery flow.

## Step 3: Update callers of send_webhook()

Find all callers of `send_webhook()` and pass the new optional parameters:

### In `notifications/dispatcher.py`:

Find where `send_webhook()` is called and update:

```python
# BEFORE:
await send_webhook(
    url=config["url"],
    method=config.get("method", "POST"),
    headers=config.get("headers", {}),
    secret=config.get("secret"),
    alert=alert_payload,
)

# AFTER:
result = await send_webhook(
    url=config["url"],
    method=config.get("method", "POST"),
    headers=config.get("headers", {}),
    secret=config.get("secret"),
    alert=alert_payload,
    audit_logger=audit_logger,    # pass from caller context
    channel_id=str(channel.get("channel_id", "")),
    tenant_id=tenant_id,
)
# Log result if needed
if not result["success"]:
    logger.warning(
        "Webhook delivery failed after %d attempts: %s",
        result["attempts"],
        result["error"],
    )
```

### In `routes/notifications.py` (test endpoint):

Find the test notification endpoint (usually `POST /notification-channels/{channel_id}/test`) and verify it uses `send_webhook()`. Update it to use the new signature:

```python
# In the test endpoint, when testing webhook/http channels:
result = await send_webhook(
    url=config["url"],
    method=config.get("method", "POST"),
    headers=config.get("headers", {}),
    secret=config.get("secret"),
    alert=TEST_PAYLOAD,
    channel_id=str(channel_id),
    tenant_id=tenant_id,
)
# Return the result to the user so they can see delivery status:
return {
    "channel_id": channel_id,
    "test": True,
    "delivery": result,
}
```

**Note:** For the test endpoint, do NOT pass `audit_logger` -- test notifications should not pollute the audit trail.

## Step 4: Update send_slack, send_pagerduty, send_teams with basic retry

While the primary focus is on `send_webhook()`, add basic error handling to the other senders so they don't silently fail:

```python
async def send_slack(webhook_url: str, alert: dict) -> dict:
    """Send alert notification to Slack."""
    payload = {
        "text": f"*[{severity_label(int(alert.get('severity', 0)))}]* {alert.get('device_id', '-')} -- {alert.get('alert_type', '-')}",
        "attachments": [
            {
                "color": severity_color(int(alert.get("severity", 0))),
                "fields": [
                    {"title": "Summary", "value": alert.get("summary", "--"), "short": False},
                    {"title": "Time", "value": str(alert.get("created_at", "--")), "short": True},
                ],
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(webhook_url, json=payload)
        return {"success": 200 <= response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        logger.warning("Slack delivery failed: %s", exc)
        return {"success": False, "error": str(exc)}
```

Apply the same pattern to `send_pagerduty` and `send_teams` -- wrap in try/except, return a result dict, log failures. Do NOT add full retry logic to these -- only to `send_webhook()`.

## Step 5: Verify the compute_webhook_signature function is importable

In `routes/notifications.py`, check if there is a "verify webhook" or "test" endpoint that reconstructs the HMAC. If receivers need to verify signatures, document the format:

```
Header: X-Signature-256
Value: sha256=<hex_digest_of_hmac_sha256(body, secret)>

Verification pseudocode:
  expected = "sha256=" + hmac_sha256(request_body_bytes, channel_secret).hex()
  actual = request.headers["X-Signature-256"]
  return hmac.compare_digest(expected, actual)
```

## Verification

```bash
# 1. Set up a webhook receiver (use webhook.site or a local server)
# Create a notification channel with a secret:
curl -s -X POST http://localhost:8080/api/v1/customer/notification-channels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{
    "name": "Test Webhook",
    "channel_type": "webhook",
    "config": {
      "url": "https://webhook.site/YOUR-UUID",
      "method": "POST",
      "secret": "my-test-secret-123"
    }
  }' | jq .

# 2. Send test notification
CHANNEL_ID=$(...)  # from step above
curl -s -X POST "http://localhost:8080/api/v1/customer/notification-channels/${CHANNEL_ID}/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" | jq .

# 3. Check webhook.site for the received request:
# - Verify header "X-Signature-256" exists
# - Verify format: "sha256=<hex>"
# - Verify HMAC:
#   echo -n '<request_body>' | openssl dgst -sha256 -hmac 'my-test-secret-123'
#   Compare output with the header value (minus "sha256=" prefix)

# 4. Test retry behavior -- set up a webhook URL that returns 503:
# Observe logs for retry attempts with delays of 1s, 5s, 25s

# 5. Test non-retryable -- set up a webhook URL that returns 404:
# Observe logs: only 1 attempt, no retry

# 6. Check audit log for delivery events
curl -s "http://localhost:8080/api/v1/customer/audit-log?category=notification" \
  -H "Authorization: Bearer $TOKEN" | jq '.events[:3]'
```

## Backward Compatibility

- The header name changes from `X-Signature-SHA256` to `X-Signature-256` and the value format changes from bare hex to `sha256=<hex>`. This is a BREAKING CHANGE for any external webhook receivers already checking the old header. If existing receivers exist, consider:
  - Sending BOTH headers during a transition period, OR
  - Documenting the change in release notes
- The `send_webhook()` function signature adds new optional keyword arguments (`audit_logger`, `channel_id`, `tenant_id`). Existing callers that don't pass these will still work -- they just won't get audit logging.
- The return type changes from `None` to `dict`. Callers that ignore the return value are unaffected.

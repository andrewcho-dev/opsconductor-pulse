# Prompt 005 — Unit Tests

## File: `tests/unit/test_subscription_expiry.py`

Read `services/subscription_worker/worker.py`.
Mock `aiosmtplib.send` using `unittest.mock.AsyncMock`.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_send_expiry_email_success` — SMTP_HOST set, aiosmtplib.send called → returns True
2. `test_send_expiry_email_no_smtp_host` — SMTP_HOST not set → returns False without SMTP call
3. `test_send_expiry_email_no_to_address` — NOTIFICATION_EMAIL_TO not set → returns False
4. `test_send_expiry_email_smtp_failure` — aiosmtplib.send raises → returns False (no crash)
5. `test_send_grace_email_uses_grace_template` — notification_type contains "grace" → subject contains "grace period"
6. `test_list_expiring_notifications_endpoint` — GET /operator/subscriptions/expiring-notifications returns list
7. `test_list_expiring_notifications_status_filter` — ?status=PENDING → WHERE clause includes status

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 7 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken

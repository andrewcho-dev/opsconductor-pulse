# Prompt 004 — Unit Tests

Read a passing test in `tests/unit/` to understand the FakeConn/FakePool pattern.

Create `tests/unit/test_alert_digest.py` with `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_get_digest_settings_returns_default` — fetchrow returns None → returns default settings (daily, empty email)
2. `test_put_digest_settings_upserts` — execute called with correct SQL → 200
3. `test_digest_job_skips_disabled` — frequency='disabled' → no email sent
4. `test_digest_job_sends_when_due` — last_sent_at is 2 days ago, frequency='daily' → send called
5. `test_digest_job_skips_if_not_due` — last_sent_at is 12 hours ago, frequency='daily' → send not called

All tests must pass under `pytest -m unit -v`.

# Task 003: Unit Tests — Delivery Pipeline (Worker, Dispatcher, Senders)

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> All tests in this task must be UNIT tests — no database, no network calls.
> Mock all external dependencies. Tests must run in < 5 seconds total.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The delivery pipeline is the most under-tested critical path:
- `worker.py` is at 58% — retry logic, backoff, stuck job recovery are untested
- `dispatcher.py` is at 71% — initialization and edge cases untested
- `delivery_worker/email_sender.py` is at 24% — actual SMTP logic untested
- `delivery_worker/snmp_sender.py` is at 23% — actual trap sending untested

These modules have complex business logic (exponential backoff, rate limiting, job state machines) that should be unit tested without infrastructure.

**Read first**:
- `services/delivery_worker/worker.py` (job processing, retry, backoff, stuck jobs)
- `services/dispatcher/dispatcher.py` (route matching, alert polling, job creation)
- `services/delivery_worker/email_sender.py` (SMTP connection, template rendering)
- `services/delivery_worker/snmp_sender.py` (trap construction, v2c vs v3)

---

## Task

### 3.1 Create `tests/unit/test_worker_logic.py`

Test the delivery worker logic from `services/delivery_worker/worker.py`. Mock `asyncpg` for all database calls and `httpx` for webhook delivery.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases for job claiming**:
- `test_claim_batch_returns_pending_jobs` — mock DB to return rows → returns job dicts
- `test_claim_batch_empty` — no pending jobs → returns empty list
- `test_claim_batch_skips_jobs_below_retry_after` — jobs with future retry_after → not claimed

**Test cases for webhook delivery**:
- `test_deliver_webhook_success` — mock httpx 200 → marks job completed
- `test_deliver_webhook_4xx_failure` — mock httpx 400 → marks job for retry
- `test_deliver_webhook_5xx_failure` — mock httpx 500 → marks job for retry
- `test_deliver_webhook_timeout` — mock httpx timeout → marks job for retry
- `test_deliver_webhook_ssrf_blocked` — internal IP → marks job failed (no retry)
- `test_deliver_webhook_network_error` — mock connection refused → marks job for retry

**Test cases for SNMP delivery**:
- `test_deliver_snmp_success` — mock snmp sender → marks job completed
- `test_deliver_snmp_failure` — mock snmp sender raises → marks job for retry

**Test cases for email delivery**:
- `test_deliver_email_success` — mock email sender → marks job completed
- `test_deliver_email_failure` — mock email sender raises → marks job for retry

**Test cases for retry logic**:
- `test_backoff_calculation_attempt_1` — verify delay is WORKER_BACKOFF_BASE_SECONDS
- `test_backoff_calculation_attempt_3` — verify exponential increase
- `test_backoff_calculation_capped` — verify delay never exceeds WORKER_BACKOFF_MAX_SECONDS
- `test_max_attempts_exhausted` — attempt count >= max → marks job permanently failed
- `test_retry_increments_attempt_count` — verify attempt_count increases by 1

**Test cases for stuck job recovery**:
- `test_recover_stuck_jobs` — jobs claimed > STUCK_JOB_MINUTES ago → reset to pending
- `test_no_stuck_jobs` — all jobs recent → nothing recovered

**Test cases for the main loop** (test one iteration, not infinite loop):
- `test_process_batch_handles_mixed_results` — some succeed, some fail → each handled correctly
- `test_process_batch_empty_is_noop` — no jobs → sleeps and returns

### 3.2 Create `tests/unit/test_dispatcher_logic.py`

Test the dispatcher from `services/dispatcher/dispatcher.py`. Mock `asyncpg`.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases for route matching**:
- `test_match_all_alerts_wildcard_route` — route with no filters → matches any alert
- `test_match_by_severity` — route filters severity=critical → matches critical, skips warning
- `test_match_by_alert_type` — route filters alert_type → matches only that type
- `test_match_by_site` — route filters site_id → matches only that site
- `test_match_by_device_prefix` — route filters device_id prefix → matches devices starting with prefix
- `test_no_match_disabled_route` — route disabled → skips
- `test_no_match_disabled_integration` — integration disabled → skips
- `test_multiple_routes_create_multiple_jobs` — one alert matches two routes → two jobs created
- `test_dedup_prevents_duplicate_jobs` — same alert+route → only one job (checked via dispatch_hash)

**Test cases for rate limiting**:
- `test_rate_limit_blocks_excess_jobs` — integration at limit → jobs not created
- `test_rate_limit_per_integration` — limits are per-integration, not global

**Test cases for alert polling**:
- `test_poll_respects_lookback_window` — only alerts within ALERT_LOOKBACK_MINUTES
- `test_poll_respects_limit` — only ALERT_LIMIT alerts per batch
- `test_poll_skips_already_dispatched` — alerts with existing jobs → skipped

### 3.3 Create `tests/unit/test_delivery_email_sender.py`

Test `services/delivery_worker/email_sender.py`. Mock `aiosmtplib`.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases**:
- `test_send_email_success` — mock SMTP → message sent
- `test_send_email_tls` — TLS config → verify starttls called
- `test_send_email_auth` — username/password config → verify login called
- `test_send_email_multiple_recipients` — to + cc + bcc → all in message headers
- `test_send_email_template_rendering` — variables substituted in subject and body
- `test_send_email_connection_refused` — mock connection error → raises with clear message
- `test_send_email_auth_failure` — mock auth error → raises with clear message
- `test_send_email_no_recipients` — empty to list → raises ValueError

### 3.4 Create `tests/unit/test_delivery_snmp_sender.py`

Test `services/delivery_worker/snmp_sender.py`. Mock pysnmp.

```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Test cases**:
- `test_send_v2c_trap` — community string config → correct SNMP v2c call
- `test_send_v3_trap` — username/auth config → correct SNMP v3 call
- `test_send_trap_timeout` — mock timeout → raises with clear message
- `test_send_trap_unreachable` — mock connection error → raises
- `test_varbind_construction` — alert data → correct OID/value pairs
- `test_unsupported_version` — version=1 → raises ValueError

---

## Files to Create

| Action | Path |
|--------|------|
| CREATE | `tests/unit/test_worker_logic.py` |
| CREATE | `tests/unit/test_dispatcher_logic.py` |
| CREATE | `tests/unit/test_delivery_email_sender.py` |
| CREATE | `tests/unit/test_delivery_snmp_sender.py` |

---

## Test

```bash
# 1. Run only the new unit tests
pytest tests/unit/test_worker_logic.py tests/unit/test_dispatcher_logic.py tests/unit/test_delivery_email_sender.py tests/unit/test_delivery_snmp_sender.py -v --tb=short

# 2. Verify they're fast
time pytest -m unit -q

# 3. Run full unit suite (including tests from task 002)
pytest -m unit -v

# 4. Check coverage improvement
pytest -m unit --cov=services/delivery_worker --cov=services/dispatcher --cov-report=term-missing -q
```

---

## Acceptance Criteria

- [ ] `test_worker_logic.py` has 20+ test cases covering job claiming, delivery, retry, backoff, stuck jobs
- [ ] `test_dispatcher_logic.py` has 12+ test cases covering route matching, rate limiting, alert polling
- [ ] `test_delivery_email_sender.py` has 8+ test cases covering SMTP, TLS, auth, templates, errors
- [ ] `test_delivery_snmp_sender.py` has 6+ test cases covering v2c, v3, errors
- [ ] ALL tests pass with `pytest -m unit`
- [ ] ALL tests run in < 5 seconds total
- [ ] No test requires database, SMTP server, or SNMP server
- [ ] `worker.py` coverage improves from 58% to > 80%
- [ ] `dispatcher.py` coverage improves from 71% to > 85%
- [ ] `delivery_worker/email_sender.py` coverage improves from 24% to > 75%
- [ ] `delivery_worker/snmp_sender.py` coverage improves from 23% to > 75%

---

## Commit

```
Add unit tests for delivery worker, dispatcher, and senders

- 45+ unit tests covering job lifecycle, retry/backoff logic,
  route matching, rate limiting, SMTP/SNMP delivery
- All mocked — no infrastructure required
- worker.py coverage: 58% → 80%+
- dispatcher.py coverage: 71% → 85%+
- email_sender.py coverage: 24% → 75%+
- snmp_sender.py coverage: 23% → 75%+

Part of Phase 9: Testing Overhaul
```

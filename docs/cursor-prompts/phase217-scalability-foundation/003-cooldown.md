# Task 3: Evaluation-Level Rule Cooldown via Valkey

## Context

`deduplicate_or_create_alert()` already prevents duplicate *alerts* by
checking for an existing OPEN alert with the same rule_id + device_id. However,
the evaluation logic still runs for every device on every cycle. At scale, a
rule that fired 30 seconds ago will be evaluated again and again, hitting
`deduplicate_or_create_alert()` every time and doing a DB write every cycle.

This task adds an evaluation-level cooldown checked in Valkey *before* the DB
is touched. If a rule fired for a device within the cooldown window, skip
evaluation entirely for that rule + device combination.

## File — services/evaluator_iot/evaluator.py

### Change 1 — Add Valkey client initialisation

After the existing `PG_POOL_MIN`/`PG_POOL_MAX` constants (around line 51),
add:

```python
VALKEY_URL = optional_env("VALKEY_URL", "redis://localhost:6379")
RULE_COOLDOWN_SECONDS = int(optional_env("RULE_COOLDOWN_SECONDS", "300"))
```

### Change 2 — Add Valkey client global and init function

After the `_window_buffers` and `_pending_tenants` globals (around line 66),
add:

```python
# Valkey client — initialised in main(), used throughout
_valkey: "redis.asyncio.Redis | None" = None
```

### Change 3 — Add imports

At the top of the file with the other imports, add:

```python
import redis.asyncio as aioredis
```

### Change 4 — Add cooldown helper functions

Add the following two functions. Place them near the other helper functions,
before `deduplicate_or_create_alert`:

```python
def _cooldown_key(tenant_id: str, rule_id: str, device_id: str) -> str:
    return f"cooldown:{tenant_id}:{rule_id}:{device_id}"


async def is_rule_on_cooldown(tenant_id: str, rule_id: str, device_id: str) -> bool:
    """Return True if this rule fired recently and should be skipped."""
    if _valkey is None or RULE_COOLDOWN_SECONDS <= 0:
        return False
    try:
        key = _cooldown_key(tenant_id, rule_id, device_id)
        return await _valkey.exists(key) == 1
    except Exception:
        # Valkey unavailable — fail open (do not skip evaluation)
        return False


async def set_rule_cooldown(tenant_id: str, rule_id: str, device_id: str) -> None:
    """Mark this rule as recently fired. Call after a NEW alert is created."""
    if _valkey is None or RULE_COOLDOWN_SECONDS <= 0:
        return
    try:
        key = _cooldown_key(tenant_id, rule_id, device_id)
        await _valkey.set(key, "1", ex=RULE_COOLDOWN_SECONDS)
    except Exception:
        logger.debug("valkey_cooldown_set_failed", exc_info=True)
```

### Change 5 — Check cooldown before evaluating each rule

Inside the per-device rule loop (the `for rule in rules:` block), add a
cooldown check as the first thing inside the loop:

```python
for rule in rules:
    rule_id = str(rule.get("rule_id") or rule.get("id", ""))

    # Skip if this rule recently fired for this device
    if await is_rule_on_cooldown(tenant_id, rule_id, device_id):
        continue

    COUNTERS["rules_evaluated"] += 1
    # ... rest of existing rule evaluation logic unchanged ...
```

### Change 6 — Set cooldown after a new alert is created

Find the call site where `deduplicate_or_create_alert()` is called and a new
alert is confirmed (`inserted` is True or `created` is True). Add cooldown
registration immediately after:

```python
    alert_id, created = await deduplicate_or_create_alert(...)
    if created:
        await set_rule_cooldown(tenant_id, rule_id, device_id)
```

(The exact variable names depend on how the result is unpacked. Look for the
`inserted` or `created` boolean returned by `deduplicate_or_create_alert` and
use that as the condition.)

### Change 7 — Initialise Valkey in main()

In `main()`, after the DB pool is created and before the evaluation loop
starts, add:

```python
    global _valkey
    try:
        _valkey = aioredis.from_url(VALKEY_URL, decode_responses=True)
        await _valkey.ping()
        log_event(logger, "valkey_connected", url=VALKEY_URL)
    except Exception as exc:
        log_event(
            logger,
            "valkey_unavailable",
            level="WARNING",
            error=str(exc),
            note="Cooldown and window state disabled; evaluation continues",
        )
        _valkey = None
```

### Change 8 — Close Valkey in shutdown

In the `finally:` block at the end of `main()`, after cancelling the listener
task, add:

```python
        if _valkey is not None:
            await _valkey.aclose()
```

## Important Notes

- Cooldown failures **fail open** — if Valkey is unreachable, `is_rule_on_cooldown`
  returns `False` and evaluation proceeds normally. Valkey being down never
  blocks alerting.
- `RULE_COOLDOWN_SECONDS=0` disables the feature entirely (returns False always).
- Cooldown is per (tenant, rule, device) — one sensor being on cooldown does
  not affect other sensors for the same rule.
- The cooldown is on *new alert creation* only. If `deduplicate_or_create_alert`
  returns `created=False` (updating an existing alert), cooldown is NOT reset —
  the existing alert's TTL continues to tick down.

## Verification

```bash
docker compose -f compose/docker-compose.yml build evaluator
docker compose -f compose/docker-compose.yml up -d evaluator
docker compose -f compose/docker-compose.yml logs evaluator | grep valkey_connected
```

Expected: `valkey_connected url=redis://iot-valkey:6379`

After a rule fires, check the cooldown key exists in Valkey:
```bash
docker compose -f compose/docker-compose.yml exec valkey \
  valkey-cli keys "cooldown:*"
```

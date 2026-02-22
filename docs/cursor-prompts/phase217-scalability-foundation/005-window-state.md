# Task 5: Move Window Buffers from Process Memory to Valkey

## Problem

`_window_buffers` (line ~66) is a process-local dict:

```python
_window_buffers: dict[tuple[str, str], deque] = {}
```

Keyed on `(device_id, rule_id)`, it holds sliding-window history for WINDOW
rules (e.g., "last 5 readings above threshold"). On any restart, redeploy, or
crash, all window history is lost. Rules with `window_seconds > 0` produce
false-negatives after every deploy until the window refills.

## Approach

Replace in-process buffer reads/writes with Valkey keys. Each buffer is stored
as a JSON list of `[timestamp, value]` pairs, with TTL = `window_seconds * 2`
(double the window duration so history survives slow reporting intervals).

Key schema: `wbuf:{tenant_id}:{rule_id}:{device_id}`

## File — services/evaluator_iot/evaluator.py

### Change 1 — Remove (or keep but stop using) _window_buffers global

The global `_window_buffers` dict can remain as a declaration for now but
must not be used as the primary read/write store after this change. It can
be removed entirely in a follow-up cleanup.

### Change 2 — Add Valkey window buffer helpers

Add these functions near the other Valkey helpers added in Task 3:

```python
def _wbuf_key(tenant_id: str, rule_id: str, device_id: str) -> str:
    return f"wbuf:{tenant_id}:{rule_id}:{device_id}"


async def wbuf_append(
    tenant_id: str,
    rule_id: str,
    device_id: str,
    ts: float,
    value: float,
    window_seconds: int,
) -> list[tuple[float, float]]:
    """
    Append (ts, value) to the Valkey window buffer for this rule+device,
    trim entries older than window_seconds, and return the current buffer.

    Falls back to empty list if Valkey is unavailable.
    """
    if _valkey is None:
        return []
    key = _wbuf_key(tenant_id, rule_id, device_id)
    ttl = max(window_seconds * 2, 120)
    cutoff = ts - window_seconds
    try:
        raw = await _valkey.get(key)
        entries: list[list[float]] = json.loads(raw) if raw else []
        # Append new entry
        entries.append([ts, value])
        # Trim entries outside the window
        entries = [e for e in entries if e[0] >= cutoff]
        await _valkey.set(key, json.dumps(entries), ex=ttl)
        return [(e[0], e[1]) for e in entries]
    except Exception:
        logger.debug("wbuf_valkey_error", exc_info=True)
        return []


async def wbuf_read(
    tenant_id: str,
    rule_id: str,
    device_id: str,
    window_seconds: int,
) -> list[tuple[float, float]]:
    """
    Read the current window buffer for this rule+device.
    Returns list of (timestamp, value) tuples within the window.
    Falls back to empty list if Valkey is unavailable.
    """
    if _valkey is None:
        return []
    key = _wbuf_key(tenant_id, rule_id, device_id)
    cutoff = time.time() - window_seconds
    try:
        raw = await _valkey.get(key)
        if not raw:
            return []
        entries = json.loads(raw)
        return [(e[0], e[1]) for e in entries if e[0] >= cutoff]
    except Exception:
        logger.debug("wbuf_valkey_read_error", exc_info=True)
        return []
```

### Change 3 — Replace _window_buffers usage with Valkey calls

Search `evaluator.py` for all sites that read from or write to
`_window_buffers`. The pattern to find:

```python
_window_buffers[...]
```

For each site:

- **Write (append a new reading to the buffer):** Replace with
  `await wbuf_append(tenant_id, rule_id, device_id, ts, value, window_seconds)`

- **Read (get current buffer for evaluation):** Replace with
  `await wbuf_read(tenant_id, rule_id, device_id, window_seconds)`

The `window_seconds` value comes from `rule.get("window_seconds")`. If
`window_seconds` is None or 0, the rule is not a sliding-window rule and
`_window_buffers` would not be accessed for it.

### Change 4 — Fail open on Valkey unavailability

Both `wbuf_append` and `wbuf_read` return empty lists when Valkey is down
(see the `except Exception` blocks above). An empty buffer means window rules
will not fire — that is the safe failure mode (false-negative rather than
false-positive). This is intentional.

## Verification

After deploying:

```bash
docker compose -f compose/docker-compose.yml build evaluator
docker compose -f compose/docker-compose.yml up -d evaluator
```

Let a device with a WINDOW rule report data for one full window period, then
restart the evaluator:

```bash
docker compose -f compose/docker-compose.yml restart evaluator
```

Check that after restart, window rule evaluation continues correctly (window
history was not lost). Inspect Valkey for window buffer keys:

```bash
docker compose -f compose/docker-compose.yml exec valkey \
  valkey-cli keys "wbuf:*"
```

Expected: one key per (tenant, rule, device) combination with active window
rules.

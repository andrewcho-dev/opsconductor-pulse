# Prompt 006 — Unit Tests for Time-Window Evaluation

## Context

`check_duration_window()` is the new function added to `evaluator.py`. It must be tested thoroughly because it is on the critical path — a bug here means alerts either never fire or fire too soon.

Add tests to `tests/unit/test_evaluator.py`. Follow the existing patterns exactly:
- `FakeConn` is already defined in that file — extend it if needed
- `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- Reference the existing `FakeConn` class which has `fetchrow`, `fetch`, `execute`

You will need to add `fetchval` support to `FakeConn` since `check_duration_window()` uses `conn.fetchval()`. Add it:

```python
class FakeConn:
    def __init__(self):
        ...
        self.fetchval_results = []  # queue of values to return
        self.fetchval_calls = []

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        if self.fetchval_results:
            return self.fetchval_results.pop(0)
        return 0
```

### Tests to add:

```python
async def test_check_duration_window_zero_returns_true_immediately():
    """duration_seconds=0 must return True without any DB query."""
    conn = FakeConn()
    result = await evaluator.check_duration_window(
        conn, "tenant-a", "device-1", "temp_c", "GT", 40.0, 0
    )
    assert result is True
    assert len(conn.fetchval_calls) == 0  # No DB query for immediate rules


async def test_check_duration_window_all_readings_breach():
    """Window fully satisfied: 0 failing readings, 5 total."""
    conn = FakeConn()
    conn.fetchval_results = [0, 5]  # failing=0, total=5
    result = await evaluator.check_duration_window(
        conn, "tenant-a", "device-1", "temp_c", "GT", 40.0, 300
    )
    assert result is True


async def test_check_duration_window_some_readings_fail():
    """Window NOT satisfied: 2 readings fail the threshold."""
    conn = FakeConn()
    conn.fetchval_results = [2, 5]  # failing=2, total=5
    result = await evaluator.check_duration_window(
        conn, "tenant-a", "device-1", "temp_c", "GT", 40.0, 300
    )
    assert result is False


async def test_check_duration_window_no_readings_in_window():
    """No data in window — cannot confirm continuous breach."""
    conn = FakeConn()
    conn.fetchval_results = [0, 0]  # failing=0, total=0 (no readings)
    result = await evaluator.check_duration_window(
        conn, "tenant-a", "device-1", "temp_c", "GT", 40.0, 300
    )
    assert result is False  # No data = not satisfied


async def test_check_duration_window_unsupported_operator():
    """Unknown operator returns False without DB query."""
    conn = FakeConn()
    result = await evaluator.check_duration_window(
        conn, "tenant-a", "device-1", "temp_c", "UNKNOWN_OP", 40.0, 300
    )
    assert result is False
    assert len(conn.fetchval_calls) == 0


async def test_check_duration_window_with_mapping():
    """With metric mapping (normalization), uses raw_metric and multiplier."""
    conn = FakeConn()
    conn.fetchval_results = [0, 3]  # failing=0, total=3
    mappings = [{"raw_metric": "temp_f", "multiplier": 0.5556, "offset_value": -17.78}]
    result = await evaluator.check_duration_window(
        conn, "tenant-a", "device-1", "temp_c", "GT", 40.0, 300,
        mappings=mappings
    )
    assert result is True
    # Confirm the query used raw_metric (temp_f), not normalized name
    assert any("temp_f" in str(call) for call in conn.fetchval_calls)


async def test_duration_seconds_zero_in_fetch_tenant_rules():
    """fetch_tenant_rules returns duration_seconds field."""
    conn = FakeConn()
    conn.fetch_result = [
        {
            "rule_id": "r1",
            "name": "High temp",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 40,
            "severity": 4,
            "site_ids": ["site-a"],
            "duration_seconds": 0,
        }
    ]
    rows = await evaluator.fetch_tenant_rules(conn, "tenant-a")
    assert "duration_seconds" in rows[0]
    assert rows[0]["duration_seconds"] == 0
```

## Acceptance Criteria

- [ ] `FakeConn` in `test_evaluator.py` has `fetchval` support
- [ ] All 7 new tests added
- [ ] `pytest tests/unit/test_evaluator.py -v` — all tests pass (new + existing)
- [ ] `pytest -m unit -v` — 0 failures across full suite

# Phase 100 — Evaluator Unit Tests

## File to create
`tests/unit/test_evaluator_logic.py`

## Pattern to follow

Look at existing unit tests in `tests/unit/` for the `FakeConn`/`FakePool` pattern used
throughout the project. Use the same pattern — do NOT add real DB dependencies.

## Tests to write

The evaluator has a function that evaluates alert rules against current device state.
Find that function in `services/evaluator/evaluator.py` — it likely takes a device record,
a rule record, and current metric values, and returns whether an alert should fire.

Write tests for the following cases:

```python
"""Unit tests for evaluator alert rule logic."""
import pytest
from evaluator.evaluator import evaluate_rule  # adjust import path as needed


class TestThresholdRules:

    def test_fires_when_above_threshold(self):
        """Alert fires when metric value exceeds threshold."""
        rule = {"rule_type": "threshold", "metric_name": "temp_c",
                "operator": ">", "threshold": 40.0, "severity": 3}
        metrics = {"temp_c": 45.0}
        assert evaluate_rule(rule, metrics) is True

    def test_does_not_fire_when_below_threshold(self):
        """Alert does NOT fire when metric value is below threshold."""
        rule = {"rule_type": "threshold", "metric_name": "temp_c",
                "operator": ">", "threshold": 40.0, "severity": 3}
        metrics = {"temp_c": 35.0}
        assert evaluate_rule(rule, metrics) is False

    def test_fires_on_exact_threshold_with_gte(self):
        rule = {"rule_type": "threshold", "metric_name": "temp_c",
                "operator": ">=", "threshold": 40.0, "severity": 3}
        metrics = {"temp_c": 40.0}
        assert evaluate_rule(rule, metrics) is True

    def test_all_operators(self):
        """All 6 comparison operators work correctly."""
        cases = [
            (">",  50.0, 40.0, True),
            (">",  30.0, 40.0, False),
            ("<",  30.0, 40.0, True),
            ("<",  50.0, 40.0, False),
            (">=", 40.0, 40.0, True),
            ("<=", 40.0, 40.0, True),
            ("==", 40.0, 40.0, True),
            ("==", 41.0, 40.0, False),
            ("!=", 41.0, 40.0, True),
            ("!=", 40.0, 40.0, False),
        ]
        for operator, value, threshold, expected in cases:
            rule = {"rule_type": "threshold", "metric_name": "x",
                    "operator": operator, "threshold": threshold}
            result = evaluate_rule(rule, {"x": value})
            assert result == expected, f"operator={operator} value={value} threshold={threshold}"

    def test_missing_metric_does_not_fire(self):
        """If the metric is not present in current readings, rule does not fire."""
        rule = {"rule_type": "threshold", "metric_name": "temp_c",
                "operator": ">", "threshold": 40.0}
        metrics = {"humidity": 80.0}  # temp_c not present
        assert evaluate_rule(rule, metrics) is False

    def test_metric_normalization_applied(self):
        """Metric value is multiplied by multiplier before comparison."""
        # If metric_mapping has multiplier=0.1, raw value 450 → normalized 45.0
        rule = {"rule_type": "threshold", "metric_name": "temp_c",
                "operator": ">", "threshold": 40.0, "multiplier": 0.1, "offset": 0}
        metrics = {"temp_c": 450}  # raw value
        assert evaluate_rule(rule, metrics) is True  # 450 * 0.1 = 45.0 > 40.0


class TestHeartbeatRules:

    def test_no_heartbeat_fires_when_stale(self):
        """NO_HEARTBEAT alert fires when last_heartbeat exceeds timeout."""
        from datetime import datetime, timezone, timedelta
        from evaluator.evaluator import should_fire_heartbeat_alert  # adjust as needed

        last_seen = datetime.now(timezone.utc) - timedelta(seconds=120)
        timeout_seconds = 30
        assert should_fire_heartbeat_alert(last_seen, timeout_seconds) is True

    def test_no_heartbeat_does_not_fire_when_recent(self):
        from datetime import datetime, timezone, timedelta
        from evaluator.evaluator import should_fire_heartbeat_alert

        last_seen = datetime.now(timezone.utc) - timedelta(seconds=10)
        timeout_seconds = 30
        assert should_fire_heartbeat_alert(last_seen, timeout_seconds) is False

    def test_no_heartbeat_fires_at_exact_boundary(self):
        from datetime import datetime, timezone, timedelta
        from evaluator.evaluator import should_fire_heartbeat_alert

        last_seen = datetime.now(timezone.utc) - timedelta(seconds=31)
        timeout_seconds = 30
        assert should_fire_heartbeat_alert(last_seen, timeout_seconds) is True
```

## Note on import paths

The exact import paths depend on how the evaluator module is structured. Read
`services/evaluator/evaluator.py` first and find the actual function names for:
- The rule evaluation function (takes rule dict + metrics dict, returns bool)
- The heartbeat check function (takes last_seen datetime + timeout, returns bool)

If these are not standalone functions but embedded in a larger class or async coroutine,
extract the pure logic into testable helper functions and test those.

## Run

```bash
pytest tests/unit/test_evaluator_logic.py -v
```

All tests must pass.

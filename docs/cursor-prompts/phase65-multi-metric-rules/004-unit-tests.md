# Prompt 004 — Unit Tests

## File: `tests/unit/test_multi_metric_rules.py`

Read `services/evaluator_iot/evaluator.py` — import `evaluate_conditions`.

Tests using `@pytest.mark.unit` (no asyncio needed for pure logic tests):

1. `test_evaluate_conditions_and_all_true` — 2 conditions, both met → True
2. `test_evaluate_conditions_and_one_false` — 2 conditions, 1 fails → False
3. `test_evaluate_conditions_or_one_true` — combinator=OR, 1 of 2 met → True
4. `test_evaluate_conditions_or_all_false` — combinator=OR, none met → False
5. `test_evaluate_conditions_missing_metric` — metric not in snapshot → condition = False
6. `test_evaluate_conditions_empty_conditions` — empty conditions list → False
7. `test_evaluate_conditions_defaults_to_and` — no combinator key → AND behavior
8. `test_api_create_rule_with_conditions` — POST with conditions dict → conditions saved (FakeConn)
9. `test_api_create_rule_without_conditions` — POST without conditions → conditions=NULL in INSERT

All `@pytest.mark.unit`.

## Acceptance Criteria

- [ ] 9 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken

"""Unit tests for multi-condition rule evaluation helpers."""

from evaluator_iot.evaluator import OPERATOR_SQL, _evaluate_single_condition


def test_gt_operator():
    assert _evaluate_single_condition(50.0, "GT", 40.0) is True
    assert _evaluate_single_condition(40.0, "GT", 40.0) is False


def test_gte_operator():
    assert _evaluate_single_condition(40.0, "GTE", 40.0) is True
    assert _evaluate_single_condition(39.9, "GTE", 40.0) is False


def test_lt_operator():
    assert _evaluate_single_condition(30.0, "LT", 40.0) is True
    assert _evaluate_single_condition(40.0, "LT", 40.0) is False


def test_lte_operator():
    assert _evaluate_single_condition(40.0, "LTE", 40.0) is True
    assert _evaluate_single_condition(40.1, "LTE", 40.0) is False


def test_none_value_returns_false():
    assert _evaluate_single_condition(None, "GT", 40.0) is False


def test_unknown_operator_returns_false():
    assert _evaluate_single_condition(50.0, "EQ", 40.0) is False


def test_operator_sql_map_complete():
    assert set(OPERATOR_SQL.keys()) == {"GT", "GTE", "LT", "LTE"}

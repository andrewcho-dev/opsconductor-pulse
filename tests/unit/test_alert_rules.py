import os
import sys
import types

import pytest

# Stub modules not available in test environment
for mod in ["asyncpg", "httpx"]:
    if mod not in sys.modules:
        sys.modules[mod] = types.SimpleNamespace(
            AsyncClient=lambda **kw: None,
            create_pool=lambda **kw: None,
            Connection=type("Connection", (), {}),
            Pool=type("Pool", (), {}),
        )
if "dateutil" not in sys.modules:
    parser_stub = types.SimpleNamespace(isoparse=lambda _v: None)
    sys.modules["dateutil"] = types.SimpleNamespace(parser=parser_stub)
    sys.modules["dateutil.parser"] = parser_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "evaluator_iot"))
from evaluator import evaluate_threshold, OPERATOR_SYMBOLS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ui_iot"))
from routes.customer import AlertRuleCreate
from pydantic import ValidationError

pytestmark = [pytest.mark.unit]


def test_gt_true():
    assert evaluate_threshold(25.0, "GT", 20.0) is True


def test_gt_false():
    assert evaluate_threshold(15.0, "GT", 20.0) is False


def test_gt_equal_is_false():
    assert evaluate_threshold(20.0, "GT", 20.0) is False


def test_lt_true():
    assert evaluate_threshold(15.0, "LT", 20.0) is True


def test_lt_false():
    assert evaluate_threshold(25.0, "LT", 20.0) is False


def test_lt_equal_is_false():
    assert evaluate_threshold(20.0, "LT", 20.0) is False


def test_gte_greater():
    assert evaluate_threshold(25.0, "GTE", 20.0) is True


def test_gte_equal():
    assert evaluate_threshold(20.0, "GTE", 20.0) is True


def test_gte_less():
    assert evaluate_threshold(15.0, "GTE", 20.0) is False


def test_lte_less():
    assert evaluate_threshold(15.0, "LTE", 20.0) is True


def test_lte_equal():
    assert evaluate_threshold(20.0, "LTE", 20.0) is True


def test_lte_greater():
    assert evaluate_threshold(25.0, "LTE", 20.0) is False


def test_none_value():
    assert evaluate_threshold(None, "GT", 20.0) is False


def test_string_numeric():
    assert evaluate_threshold("25.5", "GT", 20.0) is True


def test_string_non_numeric():
    assert evaluate_threshold("abc", "GT", 20.0) is False


def test_boolean_value():
    assert evaluate_threshold(True, "GT", 0.5) is True


def test_zero_threshold():
    assert evaluate_threshold(0.0, "LT", 0.0) is False


def test_negative_values():
    assert evaluate_threshold(-95, "LT", -80) is True


def test_unknown_operator():
    assert evaluate_threshold(25.0, "INVALID", 20.0) is False


def test_integer_value():
    assert evaluate_threshold(25, "GT", 20.0) is True


def test_operator_symbols():
    assert OPERATOR_SYMBOLS == {"GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}


def test_valid_rule_create():
    rule = AlertRuleCreate(
        name="Battery Low",
        metric_name="battery_pct",
        operator="LT",
        threshold=20.0,
        severity=4,
        description="Low battery warning",
        site_ids=["site-1", "site-2"],
        enabled=True,
    )
    assert rule.name == "Battery Low"
    assert rule.metric_name == "battery_pct"


def test_rule_create_invalid_severity():
    with pytest.raises(ValidationError):
        AlertRuleCreate(
            name="Battery Low",
            metric_name="battery_pct",
            operator="LT",
            threshold=20.0,
            severity=6,
        )


def test_rule_create_missing_name():
    with pytest.raises(ValidationError):
        AlertRuleCreate(
            metric_name="battery_pct",
            operator="LT",
            threshold=20.0,
        )

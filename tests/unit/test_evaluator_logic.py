from datetime import timedelta

import pytest

from services.evaluator_iot.evaluator import evaluate_threshold, should_fire_heartbeat_alert


def test_threshold_fires_when_above():
    assert evaluate_threshold(45.0, ">", 40.0) is True
    assert evaluate_threshold(45.0, "GT", 40.0) is True


def test_threshold_does_not_fire_when_below():
    assert evaluate_threshold(35.0, ">", 40.0) is False
    assert evaluate_threshold(35.0, "GT", 40.0) is False


def test_threshold_operator_matrix():
    cases = [
        (">", 50.0, 40.0, True),
        (">", 30.0, 40.0, False),
        ("<", 30.0, 40.0, True),
        ("<", 50.0, 40.0, False),
        (">=", 40.0, 40.0, True),
        ("<=", 40.0, 40.0, True),
        ("==", 40.0, 40.0, True),
        ("==", 41.0, 40.0, False),
        ("!=", 41.0, 40.0, True),
        ("!=", 40.0, 40.0, False),
    ]
    for operator, value, threshold, expected in cases:
        assert evaluate_threshold(value, operator, threshold) is expected


def test_missing_metric_value_does_not_fire():
    assert evaluate_threshold(None, ">", 1.0) is False


def test_heartbeat_stale_fires(monkeypatch):
    from services.evaluator_iot import evaluator

    base = evaluator.now_utc()
    monkeypatch.setattr(evaluator, "now_utc", lambda: base)
    assert should_fire_heartbeat_alert(base - timedelta(seconds=120), 30) is True


def test_heartbeat_recent_does_not_fire(monkeypatch):
    from services.evaluator_iot import evaluator

    base = evaluator.now_utc()
    monkeypatch.setattr(evaluator, "now_utc", lambda: base)
    assert should_fire_heartbeat_alert(base - timedelta(seconds=10), 30) is False


def test_heartbeat_exact_boundary_not_fired(monkeypatch):
    from services.evaluator_iot import evaluator

    base = evaluator.now_utc()
    monkeypatch.setattr(evaluator, "now_utc", lambda: base)
    assert should_fire_heartbeat_alert(base - timedelta(seconds=30), 30) is False

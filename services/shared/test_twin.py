from shared.twin import compute_structured_delta


def test_structured_delta_added():
    desired = {"led": "on", "fan": "high"}
    reported = {"led": "on"}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {"fan": "high"}
    assert result["removed"] == {}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 1


def test_structured_delta_removed():
    desired = {"led": "on"}
    reported = {"led": "on", "fan": "high"}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {}
    assert result["removed"] == {"fan": "high"}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 1


def test_structured_delta_changed():
    desired = {"led": "on", "brightness": 80}
    reported = {"led": "off", "brightness": 50}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {}
    assert result["removed"] == {}
    assert result["changed"] == {
        "brightness": {"old_value": 50, "new_value": 80},
        "led": {"old_value": "off", "new_value": "on"},
    }
    assert result["unchanged_count"] == 0


def test_structured_delta_all_synced():
    desired = {"led": "on"}
    reported = {"led": "on"}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {}
    assert result["removed"] == {}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 1


def test_structured_delta_empty():
    result = compute_structured_delta({}, {})
    assert result["added"] == {}
    assert result["removed"] == {}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 0


def test_structured_delta_complex():
    desired = {"led": "on", "temp_target": 22, "new_key": True}
    reported = {"led": "off", "temp_target": 22, "old_key": False}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {"new_key": True}
    assert result["removed"] == {"old_key": False}
    assert result["changed"] == {"led": {"old_value": "off", "new_value": "on"}}
    assert result["unchanged_count"] == 1


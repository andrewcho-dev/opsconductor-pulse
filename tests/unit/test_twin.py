from datetime import datetime, timedelta, timezone

from shared.twin import compute_delta, sync_status


def test_delta_returns_differing_keys():
    assert compute_delta({"a": 1, "b": 2}, {"a": 1, "b": 99}) == {"b": 2}


def test_delta_includes_missing_reported_keys():
    assert compute_delta({"a": 1}, {}) == {"a": 1}


def test_delta_excludes_reported_only_keys():
    assert compute_delta({}, {"a": 1}) == {}


def test_sync_status_synced():
    now = datetime.now(timezone.utc)
    assert sync_status(3, 3, now) == "synced"


def test_sync_status_pending():
    now = datetime.now(timezone.utc)
    assert sync_status(3, 2, now) == "pending"


def test_sync_status_stale_no_last_seen():
    assert sync_status(1, 1, None) == "stale"


def test_sync_status_stale_old_last_seen():
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    assert sync_status(1, 1, old) == "stale"

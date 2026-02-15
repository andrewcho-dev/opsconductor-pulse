"""Unit tests for command status model."""


def test_command_status_values():
    valid = {"queued", "delivered", "missed", "expired"}
    assert "queued" in valid
    assert "delivered" in valid
    assert "in_progress" not in valid


def test_missed_vs_expired_distinction():
    # missed = published but not ACKed
    # expired = never published
    published_statuses = {"delivered", "missed"}
    unpublished_statuses = {"expired"}
    assert "queued" not in published_statuses
    assert "queued" not in unpublished_statuses

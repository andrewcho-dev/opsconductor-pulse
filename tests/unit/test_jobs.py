def test_job_transition_queued_to_in_progress():
    allowed = {"QUEUED": {"IN_PROGRESS"}, "IN_PROGRESS": {"SUCCEEDED", "FAILED", "REJECTED"}}
    assert "IN_PROGRESS" in allowed["QUEUED"]
    assert "SUCCEEDED" in allowed["IN_PROGRESS"]
    assert "QUEUED" not in allowed["IN_PROGRESS"]


def test_terminal_statuses():
    terminal = {"SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED"}
    assert "IN_PROGRESS" not in terminal
    assert "QUEUED" not in terminal
    assert all(status in terminal for status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED"])

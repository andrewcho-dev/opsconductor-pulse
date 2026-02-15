"""Device twin helper functions."""

from datetime import datetime, timedelta, timezone

STALE_THRESHOLD_MINUTES = 30


def compute_delta(desired: dict, reported: dict) -> dict:
    """Return desired keys whose values differ from reported."""
    delta: dict = {}
    for key, desired_val in desired.items():
        if reported.get(key) != desired_val:
            delta[key] = desired_val
    return delta


def sync_status(
    desired_version: int,
    reported_version: int,
    last_seen: datetime | None,
) -> str:
    """Return shadow sync status: synced, pending, or stale."""
    if last_seen is None:
        return "stale"
    age = datetime.now(timezone.utc) - last_seen
    if age > timedelta(minutes=STALE_THRESHOLD_MINUTES):
        return "stale"
    if desired_version == reported_version:
        return "synced"
    return "pending"

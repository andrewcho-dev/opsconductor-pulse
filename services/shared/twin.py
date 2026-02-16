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


def compute_structured_delta(desired: dict, reported: dict) -> dict:
    """
    Return a structured diff between desired and reported states.

    Returns:
        {
            "added": {"key": desired_value, ...},       # in desired, not in reported
            "removed": {"key": reported_value, ...},     # in reported, not in desired
            "changed": {                                 # in both, but different values
                "key": {"old_value": reported_val, "new_value": desired_val},
                ...
            },
            "unchanged_count": int,                      # number of matching keys
        }
    """
    desired_keys = set(desired.keys())
    reported_keys = set(reported.keys())

    added_keys = desired_keys - reported_keys
    removed_keys = reported_keys - desired_keys
    common_keys = desired_keys & reported_keys

    added = {k: desired[k] for k in sorted(added_keys)}
    removed = {k: reported[k] for k in sorted(removed_keys)}

    changed: dict = {}
    unchanged_count = 0
    for k in sorted(common_keys):
        if desired[k] != reported[k]:
            changed[k] = {
                "old_value": reported[k],
                "new_value": desired[k],
            }
        else:
            unchanged_count += 1

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged_count,
    }


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

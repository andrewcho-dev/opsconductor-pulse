from datetime import datetime, timedelta, timezone


def get_current_responder(layer: dict, now: datetime) -> str:
    responders = layer.get("responders") or []
    if not responders:
        return ""
    if isinstance(responders, str):
        responders = [responders]

    shift_hours = int(layer.get("shift_duration_hours") or 168)
    handoff_day = int(layer.get("handoff_day") or 1)
    handoff_hour = int(layer.get("handoff_hour") or 9)

    now_utc = now.astimezone(timezone.utc)
    # Compute start anchor as last handoff weekday/hour before "now".
    day_delta = (now_utc.weekday() - handoff_day) % 7
    anchor = now_utc - timedelta(days=day_delta)
    anchor = anchor.replace(hour=handoff_hour, minute=0, second=0, microsecond=0)
    if anchor > now_utc:
        anchor -= timedelta(days=7)

    shift = timedelta(hours=max(1, shift_hours))
    elapsed = now_utc - anchor
    shifts_elapsed = int(elapsed.total_seconds() // shift.total_seconds())
    idx = shifts_elapsed % len(responders)
    return str(responders[idx])


def get_shift_end(layer: dict, now: datetime) -> datetime:
    shift_hours = int(layer.get("shift_duration_hours") or 168)
    handoff_day = int(layer.get("handoff_day") or 1)
    handoff_hour = int(layer.get("handoff_hour") or 9)

    now_utc = now.astimezone(timezone.utc)
    day_delta = (now_utc.weekday() - handoff_day) % 7
    anchor = now_utc - timedelta(days=day_delta)
    anchor = anchor.replace(hour=handoff_hour, minute=0, second=0, microsecond=0)
    if anchor > now_utc:
        anchor -= timedelta(days=7)
    shift = timedelta(hours=max(1, shift_hours))
    elapsed = now_utc - anchor
    shifts_elapsed = int(elapsed.total_seconds() // shift.total_seconds())
    return anchor + shift * (shifts_elapsed + 1)

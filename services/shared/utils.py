"""Shared utilities across services."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string with UTC timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def validate_uuid(value: str) -> bool:
    """Validate UUID string format."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def check_delete_result(result: str) -> bool:
    """Check if DELETE affected any rows."""
    if not result:
        return False
    parts = result.split()
    if len(parts) != 2 or parts[0] != "DELETE":
        return False
    try:
        return int(parts[1]) > 0
    except ValueError:
        return False


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not value:
        return ""
    value = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
    return value[:max_length].strip()

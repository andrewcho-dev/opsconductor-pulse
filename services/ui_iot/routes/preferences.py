from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import get_tenant_id, get_user, inject_tenant_context
from db.pool import tenant_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["preferences"])


class UserPreferencesResponse(BaseModel):
    tenant_id: str
    user_id: str
    display_name: Optional[str] = None
    timezone: str = "UTC"
    notification_prefs: dict = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    notification_prefs: Optional[dict] = None


VALID_TIMEZONES = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Vancouver",
    "America/Sao_Paulo",
    "America/Mexico_City",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Paris",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Stockholm",
    "Europe/Warsaw",
    "Europe/Moscow",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Singapore",
    "Asia/Seoul",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Asia/Bangkok",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Australia/Perth",
    "Pacific/Auckland",
    "Pacific/Honolulu",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Africa/Lagos",
]


@router.get(
    "/customer/preferences",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def get_preferences(request: Request):
    """Get current user's preferences. Returns defaults if no row exists."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user identity")

    pool = request.app.state.pool
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, user_id, display_name, timezone,
                   notification_prefs, created_at, updated_at
            FROM user_preferences
            WHERE tenant_id = $1 AND user_id = $2
            """,
            tenant_id,
            user_id,
        )

    if row:
        return {
            "tenant_id": row["tenant_id"],
            "user_id": row["user_id"],
            "display_name": row["display_name"],
            "timezone": row["timezone"],
            "notification_prefs": dict(row["notification_prefs"])
            if row["notification_prefs"]
            else {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "display_name": None,
        "timezone": "UTC",
        "notification_prefs": {},
        "created_at": None,
        "updated_at": None,
    }


@router.put(
    "/customer/preferences",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def update_preferences(payload: UpdatePreferencesRequest, request: Request):
    """Upsert the current user's preferences."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user identity")

    updates = payload.model_dump(exclude_unset=True)
    display_name_set = "display_name" in updates
    timezone_set = "timezone" in updates
    notification_prefs_set = "notification_prefs" in updates

    display_name = payload.display_name
    if display_name_set and display_name is not None:
        display_name = display_name.strip()
        if len(display_name) == 0:
            display_name = None

    timezone = payload.timezone
    if timezone_set and timezone is not None and timezone not in VALID_TIMEZONES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid timezone: {timezone}. Must be one of the supported IANA timezones."
            ),
        )

    notification_json = (
        json.dumps(payload.notification_prefs)
        if notification_prefs_set and payload.notification_prefs is not None
        else None
    )

    pool = request.app.state.pool
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_preferences (tenant_id, user_id, display_name, timezone, notification_prefs)
            VALUES ($1, $2, $3, COALESCE($4, 'UTC'), COALESCE($5::jsonb, '{}'::jsonb))
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET
                display_name = CASE WHEN $6 THEN $3 ELSE user_preferences.display_name END,
                timezone = CASE WHEN $7 THEN $4 ELSE user_preferences.timezone END,
                notification_prefs = CASE WHEN $8 THEN COALESCE($5::jsonb, '{}'::jsonb) ELSE user_preferences.notification_prefs END,
                updated_at = NOW()
            RETURNING tenant_id, user_id, display_name, timezone, notification_prefs, created_at, updated_at
            """,
            tenant_id,
            user_id,
            display_name,
            timezone,
            notification_json,
            display_name_set,
            timezone_set,
            notification_prefs_set,
        )

    return {
        "tenant_id": row["tenant_id"],
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "timezone": row["timezone"],
        "notification_prefs": dict(row["notification_prefs"]) if row["notification_prefs"] else {},
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "message": "Preferences saved",
    }


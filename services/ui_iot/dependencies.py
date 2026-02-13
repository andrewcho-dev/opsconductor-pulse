"""FastAPI dependencies for common validation patterns."""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Path, Query, Request


def valid_uuid(param_name: str = "id", description: str = "Resource ID"):
    """Dependency for UUID path parameter validation."""

    def validator(value: str = Path(..., description=description)) -> str:
        try:
            UUID(value)
            return value
        except ValueError:
            raise HTTPException(400, f"Invalid {param_name} format")

    return validator


def pagination(
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
):
    """Pagination parameters dependency."""
    return {"limit": limit, "offset": offset}


async def get_db_pool(request: Request):
    """Get database pool from app state."""
    return request.app.state.pool


ValidIntegrationId = Depends(valid_uuid("integration_id", "Integration ID"))
ValidDeviceId = Depends(valid_uuid("device_id", "Device ID"))
ValidAlertId = Depends(valid_uuid("alert_id", "Alert ID"))

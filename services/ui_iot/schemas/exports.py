"""Pydantic models for async data export."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExportFilters(BaseModel):
    """Filters applied to the export query."""

    time_range: Optional[str] = Field(
        None,
        description="Time range for data: 1h, 6h, 24h, 7d, 30d, 90d",
    )
    device_ids: Optional[list[str]] = Field(
        None,
        description="Filter to specific device IDs",
    )
    site_ids: Optional[list[str]] = Field(
        None,
        description="Filter to specific site IDs",
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status (e.g., OPEN, CLOSED for alerts; ONLINE, OFFLINE for devices)",
    )
    alert_types: Optional[list[str]] = Field(
        None,
        description="Filter alerts by type (THRESHOLD, NO_HEARTBEAT, etc.)",
    )
    metric_names: Optional[list[str]] = Field(
        None,
        description="Filter telemetry to specific metric names",
    )


class ExportCreateRequest(BaseModel):
    """Request to create a new async export job."""

    export_type: str = Field(
        ...,
        description="Type of data to export",
        pattern="^(devices|alerts|telemetry)$",
    )
    format: str = Field(
        default="csv",
        description="Output format",
        pattern="^(json|csv)$",
    )
    filters: ExportFilters = Field(
        default_factory=ExportFilters,
        description="Optional filters to narrow the export",
    )
    callback_url: Optional[str] = Field(
        None,
        description="URL to POST result notification when export completes",
    )


class ExportJobResponse(BaseModel):
    """Response for a single export job."""

    export_id: str
    tenant_id: str
    export_type: str
    format: str
    filters: dict
    status: str
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    error: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ExportCreateResponse(BaseModel):
    """Response when creating a new export job."""

    export_id: str
    status: str = "PENDING"
    estimated_rows: Optional[int] = None
    message: str = "Export job created. Poll status endpoint for progress."


class ExportListResponse(BaseModel):
    """Response listing export jobs."""

    exports: list[ExportJobResponse]
    total: int


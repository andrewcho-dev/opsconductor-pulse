"""Shared Pydantic response models for OpenAPI documentation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# --- Pagination ---

class PaginatedMeta(BaseModel):
    total: int
    limit: int
    offset: int


# --- Device responses ---

class DeviceSummary(BaseModel):
    device_id: str
    name: Optional[str] = None
    site_id: Optional[str] = None
    status: str = "OFFLINE"
    device_type: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    tags: list[str] = []
    sensor_count: int = 0
    subscription_id: Optional[str] = None
    subscription_type: Optional[str] = None
    subscription_status: Optional[str] = None


class DeviceListResponse(BaseModel):
    tenant_id: str
    devices: list[DeviceSummary]
    total: int
    limit: int
    offset: int


class DeviceDetailResponse(BaseModel):
    tenant_id: str
    device: dict[str, Any]
    events: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []


# --- Alert responses ---

class AlertSummary(BaseModel):
    alert_id: int
    tenant_id: str
    device_id: Optional[str] = None
    site_id: Optional[str] = None
    alert_type: str
    severity: int
    status: str
    summary: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    silenced_until: Optional[datetime] = None
    escalation_level: Optional[int] = None


class AlertListResponse(BaseModel):
    tenant_id: str
    alerts: list[AlertSummary]
    total: int
    status_filter: str
    limit: int
    offset: int


class AlertDetailResponse(BaseModel):
    tenant_id: str
    alert: dict[str, Any]


# --- Fleet responses ---

class FleetSummaryResponse(BaseModel):
    ONLINE: int = 0
    STALE: int = 0
    OFFLINE: int = 0
    total: int = 0
    active_alerts: int = 0


class FleetHealthResponse(BaseModel):
    total_devices: int = 0
    online: int = 0
    stale: int = 0
    offline: int = 0
    avg_uptime_pct: float = 100.0
    as_of: str


# --- Notification channel responses ---

class NotificationChannelSummary(BaseModel):
    channel_id: int
    tenant_id: str
    name: str
    channel_type: str
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class NotificationChannelListResponse(BaseModel):
    channels: list[NotificationChannelSummary]
    total: int


# --- Generic responses ---

class SuccessResponse(BaseModel):
    ok: bool = True


class DeletedResponse(BaseModel):
    deleted: bool = True


class StatusResponse(BaseModel):
    status: str
    service: str
    api_version: str


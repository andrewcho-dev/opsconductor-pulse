"""Pydantic schemas for MQTT integrations."""

from typing import Optional, Literal

from pydantic import BaseModel, Field


class MQTTIntegrationCreate(BaseModel):
    """Request body for creating MQTT integration."""

    name: str = Field(..., min_length=1, max_length=100)
    mqtt_topic: str = Field(..., min_length=1, max_length=512)
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    mqtt_retain: bool = Field(default=False)
    enabled: bool = True


class MQTTIntegrationUpdate(BaseModel):
    """Request body for updating MQTT integration."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    mqtt_topic: Optional[str] = Field(default=None, min_length=1, max_length=512)
    mqtt_qos: Optional[int] = Field(default=None, ge=0, le=2)
    mqtt_retain: Optional[bool] = None
    enabled: Optional[bool] = None


class MQTTIntegrationResponse(BaseModel):
    """Response for MQTT integration."""

    id: str
    tenant_id: str
    name: str
    type: Literal["mqtt"] = "mqtt"
    mqtt_topic: str
    mqtt_qos: int
    mqtt_retain: bool
    enabled: bool
    created_at: str
    updated_at: str

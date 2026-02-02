from enum import Enum
from typing import Optional

from pydantic import BaseModel


class IntegrationType(str, Enum):
    WEBHOOK = "webhook"
    SNMP = "snmp"


class Integration(BaseModel):
    id: str
    tenant_id: str
    name: str
    type: IntegrationType = IntegrationType.WEBHOOK
    # Webhook fields
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    # SNMP fields
    snmp_host: Optional[str] = None
    snmp_port: Optional[int] = 162
    snmp_config: Optional[dict] = None
    snmp_oid_prefix: Optional[str] = None
    # Common fields
    enabled: bool = True
    created_at: str
    updated_at: str

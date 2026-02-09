from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class SNMPVersion(str, Enum):
    V1 = "1"
    V2C = "2c"
    V3 = "3"


class SNMPAuthProtocol(str, Enum):
    MD5 = "MD5"
    SHA = "SHA"
    SHA224 = "SHA224"
    SHA256 = "SHA256"
    SHA384 = "SHA384"
    SHA512 = "SHA512"


class SNMPPrivProtocol(str, Enum):
    DES = "DES"
    AES = "AES"
    AES192 = "AES192"
    AES256 = "AES256"


class SNMPv1Config(BaseModel):
    """SNMPv1 configuration with community string."""

    version: Literal["1"] = "1"
    community: str = Field(..., min_length=1, max_length=64)


class SNMPv2cConfig(BaseModel):
    """SNMPv2c configuration with community string."""

    version: Literal["2c"] = "2c"
    community: str = Field(..., min_length=1, max_length=64)


class SNMPv3Config(BaseModel):
    """SNMPv3 configuration with authentication and privacy."""

    version: Literal["3"] = "3"
    username: str = Field(..., min_length=1, max_length=64)
    auth_protocol: SNMPAuthProtocol = SNMPAuthProtocol.SHA
    auth_password: str = Field(..., min_length=8, max_length=64)
    priv_protocol: Optional[SNMPPrivProtocol] = SNMPPrivProtocol.AES
    priv_password: Optional[str] = Field(None, min_length=8, max_length=64)

    @field_validator("priv_password")
    @classmethod
    def priv_password_required_if_priv_protocol(cls, v, info):
        if info.data.get("priv_protocol") and not v:
            raise ValueError("priv_password required when priv_protocol is set")
        return v


class SNMPIntegrationCreate(BaseModel):
    """Create SNMP integration request."""

    name: str = Field(..., min_length=1, max_length=128)
    snmp_host: str = Field(..., min_length=1, max_length=255)
    snmp_port: int = Field(default=162, ge=1, le=65535)
    snmp_config: SNMPv1Config | SNMPv2cConfig | SNMPv3Config
    snmp_oid_prefix: str = Field(default="1.3.6.1.4.1.99999", pattern=r"^[0-9.]+$")
    enabled: bool = True


class SNMPIntegrationUpdate(BaseModel):
    """Update SNMP integration request."""

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    snmp_host: Optional[str] = Field(None, min_length=1, max_length=255)
    snmp_port: Optional[int] = Field(None, ge=1, le=65535)
    snmp_config: Optional[SNMPv1Config | SNMPv2cConfig | SNMPv3Config] = None
    snmp_oid_prefix: Optional[str] = Field(None, pattern=r"^[0-9.]+$")
    enabled: Optional[bool] = None


class SNMPIntegrationResponse(BaseModel):
    """SNMP integration response (credentials masked)."""

    id: str
    tenant_id: str
    name: str
    type: Literal["snmp"] = "snmp"
    snmp_host: str
    snmp_port: int
    snmp_version: str  # "2c" or "3"
    snmp_oid_prefix: str
    enabled: bool
    created_at: str
    updated_at: str
    # Note: snmp_config credentials are NOT returned

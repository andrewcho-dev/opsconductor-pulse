"""Pydantic schemas for email integrations."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class SMTPConfig(BaseModel):
    """SMTP server configuration."""

    smtp_host: str = Field(..., min_length=1, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: Optional[str] = Field(default=None, max_length=255)
    smtp_password: Optional[str] = Field(default=None, max_length=255)
    smtp_tls: bool = Field(default=True)
    from_address: EmailStr
    from_name: Optional[str] = Field(default="OpsConductor Alerts", max_length=100)


class EmailRecipients(BaseModel):
    """Email recipient configuration."""

    to: list[EmailStr] = Field(..., min_length=1, max_length=10)
    cc: list[EmailStr] = Field(default_factory=list, max_length=10)
    bcc: list[EmailStr] = Field(default_factory=list, max_length=10)

    @field_validator("to")
    @classmethod
    def validate_to_not_empty(cls, v):
        if not v:
            raise ValueError("At least one recipient required")
        return v


class EmailTemplate(BaseModel):
    """Email template configuration."""

    subject_template: str = Field(
        default="[{severity}] {alert_type}: {device_id}",
        max_length=200,
    )
    body_template: Optional[str] = Field(default=None, max_length=10000)
    format: str = Field(default="html", pattern="^(html|text)$")


class EmailIntegrationCreate(BaseModel):
    """Request body for creating email integration."""

    name: str = Field(..., min_length=1, max_length=100)
    smtp_config: SMTPConfig
    recipients: EmailRecipients
    template: Optional[EmailTemplate] = None
    enabled: bool = True


class EmailIntegrationUpdate(BaseModel):
    """Request body for updating email integration."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    smtp_config: Optional[SMTPConfig] = None
    recipients: Optional[EmailRecipients] = None
    template: Optional[EmailTemplate] = None
    enabled: Optional[bool] = None


class EmailIntegrationResponse(BaseModel):
    """Response for email integration."""

    id: str
    tenant_id: str
    name: str
    smtp_host: str
    smtp_port: int
    smtp_tls: bool
    from_address: str
    recipient_count: int
    template_format: str
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    enabled: bool
    created_at: str
    updated_at: str

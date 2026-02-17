"""Customer organization settings endpoints."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, require_customer
from dependencies import get_db_pool
from db.pool import tenant_connection

logger = logging.getLogger("pulse.organization")

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["organization"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)

COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]


class UpdateOrganization(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    legal_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=2)  # ISO 3166-1 alpha-2
    billing_email: Optional[str] = Field(None, max_length=255)

    @field_validator("company_size")
    @classmethod
    def validate_company_size(cls, v):
        if v is not None and v not in COMPANY_SIZES:
            raise ValueError(f"company_size must be one of: {', '.join(COMPANY_SIZES)}")
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("country must be a 2-letter ISO 3166-1 alpha-2 code")
        return v.upper() if v else v


@router.get("/organization")
async def get_organization(pool=Depends(get_db_pool)):
    """Get the current tenant's organization profile."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, name, legal_name, contact_email, contact_name,
                   phone, industry, company_size,
                   address_line1, address_line2, city, state_province, postal_code, country,
                   data_residency_region, support_tier, sla_level,
                   billing_email, metadata, created_at, updated_at
            FROM tenants WHERE tenant_id = $1
            """,
            tenant_id,
        )

    if not row:
        raise HTTPException(404, "Organization not found")

    result = dict(row)
    # Handle JSONB as string (PgBouncer compat)
    if isinstance(result.get("metadata"), str):
        result["metadata"] = json.loads(result["metadata"])
    # Convert sla_level to float
    if result.get("sla_level") is not None:
        result["sla_level"] = float(result["sla_level"])
    # ISO timestamps
    for field in ("created_at", "updated_at"):
        if result.get(field):
            result[field] = result[field].isoformat() + "Z"

    return result


@router.put("/organization")
async def update_organization(
    request: Request,
    data: UpdateOrganization,
    pool=Depends(get_db_pool),
):
    """Update the current tenant's organization profile.

    Customers can edit: name, legal_name, phone, industry, company_size,
    address fields, billing_email.
    Customers CANNOT edit: tenant_id, status, data_residency_region,
    support_tier, sla_level, stripe_customer_id (operator-only).
    """
    tenant_id = get_tenant_id()
    user = get_user()

    # Build dynamic UPDATE from provided fields
    updates = []
    params = []
    idx = 1

    for field_name, value in data.model_dump(exclude_unset=True).items():
        updates.append(f"{field_name} = ${idx}")
        params.append(value)
        idx += 1

    if not updates:
        raise HTTPException(400, "No fields to update")

    updates.append("updated_at = NOW()")
    params.append(tenant_id)

    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = ${idx}",
            *params,
        )

        # Audit log
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details)
            VALUES ($1, 'TENANT_PROFILE_UPDATED', 'customer', $2, $3)
            """,
            tenant_id,
            user.get("sub") if user else None,
            json.dumps(data.model_dump(exclude_unset=True), default=str),
        )

    # Return updated profile
    return await get_organization(pool=pool)


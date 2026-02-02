import logging
from datetime import datetime

import asyncpg
from asyncpg.exceptions import UndefinedTableError

logger = logging.getLogger(__name__)


async def log_operator_access(
    conn: asyncpg.Connection,
    user_id: str,
    action: str,
    tenant_filter: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    rls_bypassed: bool = True,
) -> None:
    try:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
              (user_id, action, tenant_filter, resource_type, resource_id, ip_address, user_agent, rls_bypassed)
            VALUES ($1, $2, $3, $4, $5, $6::inet, $7, $8)
            """,
            user_id,
            action,
            tenant_filter,
            resource_type,
            resource_id,
            ip_address,
            user_agent,
            rls_bypassed,
        )
    except UndefinedTableError:
        logger.warning("operator_audit_log table missing; audit skipped")
    except Exception:
        logger.exception("Failed to write operator audit log")


async def fetch_operator_audit_log(
    conn: asyncpg.Connection,
    user_id: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    """Fetch audit log entries for compliance review."""
    rows = await conn.fetch(
        """
        SELECT id, user_id, action, tenant_filter, resource_type,
               resource_id, ip_address, user_agent, rls_bypassed, created_at
        FROM operator_audit_log
        WHERE ($1::text IS NULL OR user_id = $1)
          AND ($2::text IS NULL OR action = $2)
          AND ($3::timestamptz IS NULL OR created_at >= $3)
        ORDER BY created_at DESC
        LIMIT $4
        """,
        user_id,
        action,
        since,
        limit,
    )
    return [dict(r) for r in rows]

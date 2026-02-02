import logging
from typing import Optional

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
) -> None:
    try:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
              (user_id, action, tenant_filter, resource_type, resource_id, ip_address, user_agent)
            VALUES ($1, $2, $3, $4, $5, $6::inet, $7)
            """,
            user_id,
            action,
            tenant_filter,
            resource_type,
            resource_id,
            ip_address,
            user_agent,
        )
    except UndefinedTableError:
        logger.warning("operator_audit_log table missing; audit skipped")
    except Exception:
        logger.exception("Failed to write operator audit log")

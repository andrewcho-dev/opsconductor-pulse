import logging
from datetime import timedelta

import httpx

logger = logging.getLogger(__name__)


async def run_escalation_tick(pool):
    """
    Called every 60s. Escalates OPEN alerts that reached next_escalation_at.
    """
    async with pool.acquire() as conn:
        due_rows = await conn.fetch(
            """
            SELECT fa.id, fa.tenant_id, fa.device_id, fa.summary, fa.escalation_level,
                   ar.escalation_policy_id
            FROM fleet_alert fa
            LEFT JOIN alert_rules ar
              ON ar.tenant_id = fa.tenant_id
             AND (ar.id::text = COALESCE(fa.details->>'rule_id', ''))
            WHERE fa.status = 'OPEN'
              AND fa.next_escalation_at IS NOT NULL
              AND fa.next_escalation_at <= NOW()
            LIMIT 200
            """
        )

        for row in due_rows:
            policy_id = row["escalation_policy_id"]
            if not policy_id:
                await conn.execute(
                    "UPDATE fleet_alert SET next_escalation_at = NULL WHERE id = $1",
                    row["id"],
                )
                continue

            next_level_no = int(row["escalation_level"] or 0) + 1
            level = await conn.fetchrow(
                """
                SELECT level_number, delay_minutes, notify_email, notify_webhook
                FROM escalation_levels
                WHERE policy_id = $1 AND level_number = $2
                """,
                policy_id,
                next_level_no,
            )

            if not level:
                await conn.execute(
                    "UPDATE fleet_alert SET next_escalation_at = NULL WHERE id = $1",
                    row["id"],
                )
                continue

            payload = {
                "alert_id": row["id"],
                "tenant_id": row["tenant_id"],
                "device_id": row["device_id"],
                "summary": row["summary"],
                "escalation_level": next_level_no,
            }
            webhook = level["notify_webhook"]
            if webhook:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        await client.post(webhook, json=payload)
                except Exception:
                    logger.exception("Escalation webhook send failed")

            email = level["notify_email"]
            if email:
                logger.info(
                    "Escalation email placeholder",
                    extra={"to": email, "alert_id": row["id"], "level": next_level_no},
                )

            await conn.execute(
                """
                UPDATE fleet_alert
                SET escalation_level = $2,
                    escalated_at = NOW(),
                    next_escalation_at = NOW() + $3::interval
                WHERE id = $1
                """,
                row["id"],
                next_level_no,
                timedelta(minutes=int(level["delay_minutes"])),
            )

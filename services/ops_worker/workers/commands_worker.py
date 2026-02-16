import uuid

from shared.logging import get_logger, trace_id_var

logger = get_logger("pulse.commands_worker")


async def run_commands_expiry_tick(pool) -> None:
    """
    Mark queued commands as missed or expired after expires_at passes.
    """
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        async with pool.acquire() as conn:
            missed = await conn.execute(
                """
                UPDATE device_commands
                SET status = 'missed'
                WHERE status = 'queued'
                  AND expires_at <= NOW()
                  AND published_at IS NOT NULL
                """
            )
            expired = await conn.execute(
                """
                UPDATE device_commands
                SET status = 'expired'
                WHERE status = 'queued'
                  AND expires_at <= NOW()
                  AND published_at IS NULL
                """
            )
            total = int(missed.split()[-1]) + int(expired.split()[-1])
            if total > 0:
                logger.info(
                    "commands_expiry_tick",
                    extra={"missed": int(missed.split()[-1]), "expired": int(expired.split()[-1])},
                )
    except Exception as exc:
        logger.exception("commands_expiry_tick_error", extra={"error": str(exc)})
    finally:
        trace_id_var.reset(token)

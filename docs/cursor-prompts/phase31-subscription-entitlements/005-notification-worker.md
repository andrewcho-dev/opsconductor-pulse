# 005: Subscription Notification Worker

## Task

Create a background worker service for:
1. Subscription state transitions (ACTIVE → GRACE → SUSPENDED)
2. Renewal notification scheduling
3. Device count reconciliation

## File to Create

`services/subscription_worker/worker.py`

## Directory Structure

Create the service directory:
```
services/subscription_worker/
├── __init__.py
├── worker.py
└── Dockerfile
```

## Worker Implementation

```python
"""
Subscription Worker

Runs periodic jobs:
1. State transitions (every 5 minutes)
2. Notification scheduling (every hour)
3. Device count reconciliation (daily at midnight)
"""

import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

GRACE_PERIOD_DAYS = 14
NOTIFICATION_DAYS = [90, 60, 30, 14, 7, 1]


async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        min_size=1,
        max_size=3,
    )


async def process_state_transitions(pool: asyncpg.Pool) -> None:
    """
    Handle subscription state transitions:
    - ACTIVE → GRACE when term_end has passed
    - GRACE → SUSPENDED when grace_end has passed
    """
    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)

        # ACTIVE → GRACE (term expired, start grace period)
        rows = await conn.fetch(
            """
            UPDATE tenant_subscription
            SET status = 'GRACE',
                grace_end = term_end + interval '14 days',
                updated_at = now()
            WHERE status = 'ACTIVE'
              AND term_end < $1
            RETURNING tenant_id, term_end
            """,
            now
        )
        for row in rows:
            logger.info(f"Tenant {row['tenant_id']} moved to GRACE (term ended {row['term_end']})")
            await log_audit(conn, row['tenant_id'], 'GRACE_STARTED', 'system')

        # GRACE → SUSPENDED (grace period expired)
        rows = await conn.fetch(
            """
            UPDATE tenant_subscription
            SET status = 'SUSPENDED',
                updated_at = now()
            WHERE status = 'GRACE'
              AND grace_end < $1
            RETURNING tenant_id, grace_end
            """,
            now
        )
        for row in rows:
            logger.info(f"Tenant {row['tenant_id']} moved to SUSPENDED (grace ended {row['grace_end']})")
            await log_audit(conn, row['tenant_id'], 'SUSPENDED', 'system')


async def schedule_renewal_notifications(pool: asyncpg.Pool) -> None:
    """
    Schedule renewal notifications for subscriptions expiring soon.
    Creates notification records for: 90, 60, 30, 14, 7, 1 days before expiry.
    """
    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)

        for days in NOTIFICATION_DAYS:
            target_date = now + timedelta(days=days)
            notification_type = f'RENEWAL_{days}'

            # Find subscriptions expiring on target date that don't have this notification scheduled
            rows = await conn.fetch(
                """
                SELECT ts.tenant_id, ts.term_end
                FROM tenant_subscription ts
                WHERE ts.status = 'ACTIVE'
                  AND DATE(ts.term_end) = DATE($1)
                  AND NOT EXISTS (
                      SELECT 1 FROM subscription_notifications sn
                      WHERE sn.tenant_id = ts.tenant_id
                        AND sn.notification_type = $2
                        AND DATE(sn.scheduled_at) = DATE($1)
                  )
                """,
                target_date,
                notification_type
            )

            for row in rows:
                await conn.execute(
                    """
                    INSERT INTO subscription_notifications
                        (tenant_id, notification_type, scheduled_at, channel, status)
                    VALUES ($1, $2, $3, 'email', 'PENDING')
                    """,
                    row['tenant_id'],
                    notification_type,
                    now
                )
                logger.info(f"Scheduled {notification_type} for tenant {row['tenant_id']}")


async def process_pending_notifications(pool: asyncpg.Pool) -> None:
    """
    Process pending notifications and mark them as sent.
    In production, this would integrate with email service.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT sn.id, sn.tenant_id, sn.notification_type, t.contact_email
            FROM subscription_notifications sn
            JOIN tenants t ON t.tenant_id = sn.tenant_id
            WHERE sn.status = 'PENDING'
              AND sn.scheduled_at <= now()
            LIMIT 100
            """
        )

        for row in rows:
            # TODO: Send actual email via email service
            # For now, just mark as sent
            logger.info(f"Would send {row['notification_type']} to {row['contact_email']} for tenant {row['tenant_id']}")

            await conn.execute(
                """
                UPDATE subscription_notifications
                SET status = 'SENT', sent_at = now()
                WHERE id = $1
                """,
                row['id']
            )


async def reconcile_device_counts(pool: asyncpg.Pool) -> None:
    """
    Nightly job to reconcile active_device_count with actual device count.
    Fixes any drift from race conditions or bugs.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE tenant_subscription ts
            SET active_device_count = (
                SELECT COUNT(*)
                FROM device_registry dr
                WHERE dr.tenant_id = ts.tenant_id
                  AND dr.status = 'ACTIVE'
            ),
            updated_at = now()
            WHERE active_device_count != (
                SELECT COUNT(*)
                FROM device_registry dr
                WHERE dr.tenant_id = ts.tenant_id
                  AND dr.status = 'ACTIVE'
            )
            RETURNING tenant_id, active_device_count
            """
        )

        for row in rows:
            logger.info(f"Reconciled device count for {row['tenant_id']}: {row['active_device_count']}")


async def log_audit(conn: asyncpg.Connection, tenant_id: str, event_type: str, actor_type: str) -> None:
    """Insert audit log entry."""
    await conn.execute(
        """
        INSERT INTO subscription_audit
            (tenant_id, event_type, actor_type)
        VALUES ($1, $2, $3)
        """,
        tenant_id,
        event_type,
        actor_type
    )


async def run_worker() -> None:
    """Main worker loop."""
    logger.info("Starting subscription worker...")

    pool = await get_pool()
    logger.info("Database connected")

    last_reconcile = datetime.now(timezone.utc)

    while True:
        try:
            # State transitions - every 5 minutes
            await process_state_transitions(pool)

            # Notifications - every iteration
            await schedule_renewal_notifications(pool)
            await process_pending_notifications(pool)

            # Device count reconciliation - once per day
            now = datetime.now(timezone.utc)
            if now.hour == 0 and (now - last_reconcile).total_seconds() > 3600:
                await reconcile_device_counts(pool)
                last_reconcile = now

        except Exception as e:
            logger.exception(f"Worker error: {e}")

        await asyncio.sleep(300)  # 5 minutes


if __name__ == "__main__":
    asyncio.run(run_worker())
```

## Dockerfile

Create `services/subscription_worker/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install asyncpg

COPY worker.py .

CMD ["python", "worker.py"]
```

## Docker Compose Addition

Add to `docker-compose.yml`:

```yaml
  subscription-worker:
    build:
      context: ./services/subscription_worker
    environment:
      - PG_HOST=iot-postgres
      - PG_PORT=5432
      - PG_DB=iotcloud
      - PG_USER=iot
      - PG_PASS=iot_dev
    depends_on:
      - iot-postgres
    restart: unless-stopped
```

## Testing

```bash
# Test state transition
UPDATE tenant_subscription SET term_end = now() - interval '1 day' WHERE tenant_id = 'test-tenant';
# Wait 5 minutes or restart worker
# Check: SELECT status FROM tenant_subscription WHERE tenant_id = 'test-tenant';
# Should be 'GRACE'

# Test notification scheduling
UPDATE tenant_subscription SET term_end = now() + interval '30 days' WHERE tenant_id = 'test-tenant';
# Wait for worker run
# Check: SELECT * FROM subscription_notifications WHERE tenant_id = 'test-tenant';
```

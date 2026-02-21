# 002: Subscription Notification Worker

## Task

Implement a scheduled job to send expiry notifications and process subscription state transitions.

## Files to Create

1. `services/subscription_worker/worker.py`
2. `services/subscription_worker/Dockerfile`
3. Update `compose/docker-compose.yml`

## 1. Worker Implementation

**File:** `services/subscription_worker/worker.py`

```python
"""
Subscription Worker - Scheduled job for:
1. Sending renewal notifications at 90, 60, 30, 14, 7, 1 days before expiry
2. Transitioning ACTIVE → GRACE when term_end passes
3. Transitioning GRACE → SUSPENDED when grace_end passes
4. Reconciling device counts nightly
"""
import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import asyncpg
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://iot:iot_dev@postgres:5432/iotcloud")
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL")  # Optional external webhook
NOTIFICATION_DAYS = [90, 60, 30, 14, 7, 1]
GRACE_PERIOD_DAYS = 14


async def get_pool():
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)


async def schedule_renewal_notifications(pool: asyncpg.Pool):
    """
    Find subscriptions expiring within notification windows and create notification records.
    """
    async with pool.acquire() as conn:
        for days in NOTIFICATION_DAYS:
            notification_type = f"RENEWAL_{days}"
            target_date = datetime.now(timezone.utc) + timedelta(days=days)

            # Find subscriptions expiring on target date (within 24h window)
            rows = await conn.fetch(
                """
                SELECT s.subscription_id, s.tenant_id, s.term_end, t.name as tenant_name
                FROM subscriptions s
                JOIN tenants t ON t.tenant_id = s.tenant_id
                WHERE s.status = 'ACTIVE'
                  AND s.term_end >= $1
                  AND s.term_end < $1 + interval '1 day'
                  AND NOT EXISTS (
                      SELECT 1 FROM subscription_notifications n
                      WHERE n.tenant_id = s.tenant_id
                        AND n.notification_type = $2
                        AND n.scheduled_at >= $1 - interval '1 day'
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
                    VALUES ($1, $2, now(), 'email', 'PENDING')
                    """,
                    row['tenant_id'],
                    notification_type
                )
                logger.info(f"Scheduled {notification_type} notification for {row['tenant_id']}")


async def process_pending_notifications(pool: asyncpg.Pool):
    """
    Send pending notifications via configured channels.
    """
    async with pool.acquire() as conn:
        pending = await conn.fetch(
            """
            SELECT n.id, n.tenant_id, n.notification_type, t.name as tenant_name,
                   s.term_end, s.device_limit, s.active_device_count
            FROM subscription_notifications n
            JOIN tenants t ON t.tenant_id = n.tenant_id
            JOIN subscriptions s ON s.tenant_id = n.tenant_id AND s.subscription_type = 'MAIN'
            WHERE n.status = 'PENDING'
              AND n.scheduled_at <= now()
            ORDER BY n.scheduled_at
            LIMIT 100
            """
        )

        for row in pending:
            try:
                # Send notification (implement your channel here)
                await send_notification(row)

                await conn.execute(
                    """
                    UPDATE subscription_notifications
                    SET status = 'SENT', sent_at = now()
                    WHERE id = $1
                    """,
                    row['id']
                )
                logger.info(f"Sent {row['notification_type']} to {row['tenant_id']}")

            except Exception as e:
                await conn.execute(
                    """
                    UPDATE subscription_notifications
                    SET status = 'FAILED', error = $2
                    WHERE id = $1
                    """,
                    row['id'],
                    str(e)
                )
                logger.error(f"Failed to send notification {row['id']}: {e}")


async def send_notification(row: dict):
    """
    Send notification via configured channel.
    Implement email, webhook, or in-app notification here.
    """
    if NOTIFICATION_WEBHOOK_URL:
        async with httpx.AsyncClient() as client:
            await client.post(
                NOTIFICATION_WEBHOOK_URL,
                json={
                    "tenant_id": row['tenant_id'],
                    "tenant_name": row['tenant_name'],
                    "notification_type": row['notification_type'],
                    "term_end": row['term_end'].isoformat() if row['term_end'] else None,
                    "device_limit": row['device_limit'],
                    "active_device_count": row['active_device_count'],
                },
                timeout=30.0
            )
    else:
        # Log-only mode for now
        logger.info(f"NOTIFICATION: {row['notification_type']} for tenant {row['tenant_name']} ({row['tenant_id']})")


async def process_grace_transitions(pool: asyncpg.Pool):
    """
    Transition subscriptions:
    - ACTIVE → GRACE when term_end has passed
    - GRACE → SUSPENDED when grace_end has passed
    """
    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)

        # ACTIVE → GRACE
        rows = await conn.fetch(
            """
            UPDATE subscriptions
            SET status = 'GRACE',
                grace_end = term_end + interval '14 days',
                updated_at = now()
            WHERE status = 'ACTIVE'
              AND term_end < $1
            RETURNING subscription_id, tenant_id
            """,
            now
        )

        for row in rows:
            logger.info(f"Transitioned {row['subscription_id']} to GRACE")
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'GRACE_STARTED', 'system', 'subscription-worker', $2)
                """,
                row['tenant_id'],
                f'{{"subscription_id": "{row["subscription_id"]}"}}'
            )

            # Schedule grace notifications
            await conn.execute(
                """
                INSERT INTO subscription_notifications
                    (tenant_id, notification_type, scheduled_at, channel, status)
                VALUES ($1, 'GRACE_START', now(), 'email', 'PENDING')
                """,
                row['tenant_id']
            )

        # GRACE → SUSPENDED
        rows = await conn.fetch(
            """
            UPDATE subscriptions
            SET status = 'SUSPENDED',
                updated_at = now()
            WHERE status = 'GRACE'
              AND grace_end < $1
            RETURNING subscription_id, tenant_id
            """,
            now
        )

        for row in rows:
            logger.info(f"Transitioned {row['subscription_id']} to SUSPENDED")
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STATUS_SUSPENDED', 'system', 'subscription-worker', $2)
                """,
                row['tenant_id'],
                f'{{"subscription_id": "{row["subscription_id"]}", "reason": "grace_period_expired"}}'
            )

            await conn.execute(
                """
                INSERT INTO subscription_notifications
                    (tenant_id, notification_type, scheduled_at, channel, status)
                VALUES ($1, 'SUSPENDED', now(), 'email', 'PENDING')
                """,
                row['tenant_id']
            )


async def reconcile_device_counts(pool: asyncpg.Pool):
    """
    Nightly reconciliation of active_device_count with actual device_registry counts.
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE subscriptions s
            SET active_device_count = (
                SELECT COUNT(*)
                FROM device_registry dr
                WHERE dr.subscription_id = s.subscription_id
                  AND dr.status = 'ACTIVE'
            ),
            updated_at = now()
            WHERE active_device_count != (
                SELECT COUNT(*)
                FROM device_registry dr
                WHERE dr.subscription_id = s.subscription_id
                  AND dr.status = 'ACTIVE'
            )
            """
        )

        count = int(result.split()[-1]) if result else 0
        if count > 0:
            logger.info(f"Reconciled device counts for {count} subscriptions")


async def run_once():
    """Run all worker tasks once."""
    pool = await get_pool()
    try:
        logger.info("Starting subscription worker run...")

        await schedule_renewal_notifications(pool)
        await process_pending_notifications(pool)
        await process_grace_transitions(pool)
        await reconcile_device_counts(pool)

        logger.info("Subscription worker run complete")
    finally:
        await pool.close()


async def run_loop(interval_seconds: int = 3600):
    """Run worker tasks in a loop."""
    pool = await get_pool()
    try:
        while True:
            logger.info("Starting subscription worker run...")

            try:
                await schedule_renewal_notifications(pool)
                await process_pending_notifications(pool)
                await process_grace_transitions(pool)
                await reconcile_device_counts(pool)
            except Exception as e:
                logger.error(f"Worker run failed: {e}")

            logger.info(f"Sleeping for {interval_seconds} seconds...")
            await asyncio.sleep(interval_seconds)
    finally:
        await pool.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        asyncio.run(run_once())
    else:
        # Default: run every hour
        interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "3600"))
        asyncio.run(run_loop(interval))
```

## 2. Dockerfile

**File:** `services/subscription_worker/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir asyncpg httpx

COPY worker.py .

CMD ["python", "worker.py"]
```

## 3. Docker Compose Service

Add to `compose/docker-compose.yml`:

```yaml
  subscription-worker:
    build:
      context: ../services/subscription_worker
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://iot:iot_dev@postgres:5432/iotcloud
      WORKER_INTERVAL_SECONDS: "3600"
      # NOTIFICATION_WEBHOOK_URL: "https://your-webhook.example.com/notify"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - iot-net
```

## 4. Manual Run (for testing)

```bash
# Run once
docker compose -f compose/docker-compose.yml run --rm subscription-worker python worker.py --once

# Check logs
docker compose -f compose/docker-compose.yml logs subscription-worker
```

## Verification

1. Create a subscription with term_end = now + 7 days
2. Run worker once
3. Check subscription_notifications table for RENEWAL_7 record
4. Set subscription term_end = now - 1 day, status = ACTIVE
5. Run worker once
6. Verify status changed to GRACE and grace_end is set
7. Check subscription_audit for GRACE_STARTED event

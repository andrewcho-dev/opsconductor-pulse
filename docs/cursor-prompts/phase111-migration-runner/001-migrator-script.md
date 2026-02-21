# Phase 111 — db/migrate.py

## File to create
`db/migrate.py`

```python
#!/usr/bin/env python3
"""
OpsConductor-Pulse database migration runner.

Usage:
    python3 db/migrate.py

Reads DATABASE_URL from environment. Applies all *.sql files in
db/migrations/ in numeric filename order. Skips already-applied migrations.
Exits non-zero on any error — safe to use as a Docker init container.
"""

import os
import sys
import re
import logging
from pathlib import Path

import psycopg2
import psycopg2.extensions

logging.basicConfig(
    level=logging.INFO,
    format='{"ts": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("migrator")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT        NOT NULL PRIMARY KEY,
    filename    TEXT        NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def get_connection():
    url = os.environ.get("DATABASE_URL") or os.environ.get("NOTIFY_DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)
    # Use direct postgres URL (not pgbouncer) — DDL requires session-mode connection
    # If DATABASE_URL points to pgbouncer, override with NOTIFY_DATABASE_URL
    # which points directly to postgres.
    direct_url = os.environ.get("NOTIFY_DATABASE_URL") or url
    logger.info(f"Connecting to database")
    return psycopg2.connect(direct_url)


def get_migration_files() -> list[tuple[str, Path]]:
    """
    Returns list of (version, path) tuples sorted by version number.
    Version is the numeric prefix of the filename (e.g. "001" from "001_init.sql").
    """
    files = []
    for f in MIGRATIONS_DIR.glob("*.sql"):
        m = re.match(r"^(\d+)", f.name)
        if m:
            files.append((m.group(1), f))
    return sorted(files, key=lambda x: int(x[0]))


def run_migrations(conn) -> int:
    """Apply pending migrations. Returns count of migrations applied."""
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(CREATE_TRACKING_TABLE)
        conn.commit()

    migration_files = get_migration_files()
    if not migration_files:
        logger.warning(f"No migration files found in {MIGRATIONS_DIR}")
        return 0

    applied = 0
    for version, path in migration_files:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (version,),
            )
            if cur.fetchone():
                logger.info(f"Skipping {path.name} — already applied")
                continue

        logger.info(f"Applying {path.name}")
        sql = path.read_text(encoding="utf-8")

        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                    (version, path.name),
                )
            conn.commit()
            logger.info(f"Applied {path.name} successfully")
            applied += 1
        except Exception as exc:
            conn.rollback()
            logger.error(f"Migration {path.name} FAILED: {exc}")
            sys.exit(1)

    return applied


def main():
    logger.info("Starting migration runner")
    conn = get_connection()
    try:
        applied = run_migrations(conn)
        logger.info(f"Migration complete. {applied} migration(s) applied.")
    finally:
        conn.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
```

## File to create
`db/Dockerfile.migrator`

```dockerfile
FROM python:3.11-slim

RUN pip install --no-cache-dir psycopg2-binary

WORKDIR /app
COPY migrations/ ./migrations/
COPY migrate.py ./migrate.py

CMD ["python3", "migrate.py"]
```

## Notes

- Uses `psycopg2` (sync) — appropriate for a one-shot init container.
- Uses `NOTIFY_DATABASE_URL` (direct Postgres connection) for DDL — pgbouncer
  in transaction mode cannot handle DDL reliably.
- Exits non-zero on any failure — Docker will not start dependent services
  if the migrator fails (when using `depends_on: condition: service_completed_successfully`).
- The `schema_migrations` table itself is created idempotently — safe to run
  on a fresh or existing database.

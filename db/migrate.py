#!/usr/bin/env python3
"""
OpsConductor-Pulse database migration runner.

Usage:
    python3 db/migrate.py

Reads DATABASE_URL from environment. Applies all *.sql files in
db/migrations/ in numeric filename order. Skips already-applied migrations.
Exits non-zero on any error.
"""

import logging
import os
import re
import sys
from pathlib import Path

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
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
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("NOTIFY_DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)
    direct_url = os.environ.get("NOTIFY_DATABASE_URL") or db_url
    logger.info("Connecting to database")
    return psycopg2.connect(direct_url)


def get_migration_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for file_path in MIGRATIONS_DIR.glob("*.sql"):
        match = re.match(r"^(\d+)", file_path.name)
        if match:
            files.append((match.group(1), file_path))
    return sorted(files, key=lambda item: int(item[0]))


def run_migrations(conn) -> int:
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute(CREATE_TRACKING_TABLE)
        conn.commit()

    migration_files = get_migration_files()
    if not migration_files:
        logger.warning(f"No migration files found in {MIGRATIONS_DIR}")
        return 0

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM schema_migrations")
        tracked_count = int(cur.fetchone()[0] or 0)
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name != 'schema_migrations'
            """
        )
        existing_table_count = int(cur.fetchone()[0] or 0)

    # Legacy bootstrap: DB already has schema objects but no tracking rows.
    # Mark current migration set as applied to avoid replaying old SQL that
    # may not be idempotent against a long-lived database.
    if tracked_count == 0 and existing_table_count > 0:
        logger.info("Bootstrapping schema_migrations for existing database")
        with conn.cursor() as cur:
            for version, file_path in migration_files:
                cur.execute(
                    """
                    INSERT INTO schema_migrations (version, filename)
                    VALUES (%s, %s)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    (version, file_path.name),
                )
        conn.commit()
        return 0

    applied_count = 0
    for version, file_path in migration_files:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (version,),
            )
            if cur.fetchone():
                logger.info(f"Skipping {file_path.name} — already applied")
                continue

        logger.info(f"Applying {file_path.name}")
        sql = file_path.read_text(encoding="utf-8")

        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                    (version, file_path.name),
                )
            conn.commit()
            logger.info(f"Applied {file_path.name} successfully")
            applied_count += 1
        except Exception as exc:
            conn.rollback()
            logger.error(f"Migration {file_path.name} FAILED: {exc}")
            sys.exit(1)

    return applied_count


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

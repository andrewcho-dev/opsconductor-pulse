# Phase 29.4: System Capacity API

## Task

Create `/operator/system/capacity` endpoint that returns disk usage, database sizes, and connection utilization.

---

## Add Capacity Endpoint

**File:** `services/ui_iot/routes/system.py`

Add to the existing system router:

```python
import shutil

@router.get("/capacity")
async def get_system_capacity(request: Request):
    """
    Get system capacity and utilization metrics.
    Includes disk usage, database sizes, and connection counts.
    """
    import asyncio

    # Run checks in parallel
    postgres_stats, influx_stats, disk_stats = await asyncio.gather(
        get_postgres_capacity(),
        get_influxdb_capacity(),
        get_disk_capacity(),
        return_exceptions=True,
    )

    # Handle exceptions
    if isinstance(postgres_stats, Exception):
        postgres_stats = {"error": str(postgres_stats)}
    if isinstance(influx_stats, Exception):
        influx_stats = {"error": str(influx_stats)}
    if isinstance(disk_stats, Exception):
        disk_stats = {"error": str(disk_stats)}

    return {
        "postgres": postgres_stats,
        "influxdb": influx_stats,
        "disk": disk_stats,
    }


async def get_postgres_capacity() -> dict:
    """Get PostgreSQL capacity metrics."""
    try:
        conn = await asyncpg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            timeout=5,
        )

        # Database size
        db_size = await conn.fetchval(
            "SELECT pg_database_size($1)", POSTGRES_DB
        )

        # Connection stats
        connections = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
            POSTGRES_DB,
        )
        max_conn = await conn.fetchval("SHOW max_connections")

        # Table sizes (top 10)
        table_sizes = await conn.fetch(
            """
            SELECT
                schemaname || '.' || relname as table_name,
                pg_total_relation_size(relid) as total_size,
                pg_relation_size(relid) as data_size,
                pg_indexes_size(relid) as index_size
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC
            LIMIT 10
            """
        )

        await conn.close()

        return {
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "connections_used": connections,
            "connections_max": int(max_conn),
            "connections_pct": round(connections / int(max_conn) * 100, 1),
            "top_tables": [
                {
                    "name": r["table_name"],
                    "total_mb": round(r["total_size"] / (1024 * 1024), 2),
                    "data_mb": round(r["data_size"] / (1024 * 1024), 2),
                    "index_mb": round(r["index_size"] / (1024 * 1024), 2),
                }
                for r in table_sizes
            ],
        }
    except Exception as e:
        logger.error("Failed to get Postgres capacity: %s", e)
        raise


async def get_influxdb_capacity() -> dict:
    """Get InfluxDB capacity metrics."""
    try:
        # Check file count (this is what we limit)
        # Note: This requires access to the file system or an API endpoint
        # For now, we'll use environment variable for the limit
        file_limit = int(os.getenv("INFLUXDB_FILE_LIMIT", "1000"))

        # Try to get database list and sizes
        async with httpx.AsyncClient(timeout=10.0) as client:
            # List databases
            resp = await client.get(
                f"{INFLUXDB_URL}/api/v3/databases",
                headers={"Authorization": f"Bearer {INFLUXDB_TOKEN}"},
            )

            databases = []
            if resp.status_code == 200:
                try:
                    databases = resp.json()
                except Exception:
                    pass

        return {
            "file_limit": file_limit,
            "database_count": len(databases) if isinstance(databases, list) else 0,
            "databases": databases[:20] if isinstance(databases, list) else [],
        }
    except Exception as e:
        logger.error("Failed to get InfluxDB capacity: %s", e)
        raise


def get_disk_capacity() -> dict:
    """Get disk capacity for data volumes."""
    # Check the root filesystem (or specific mount points if known)
    try:
        # Get disk usage for common paths
        paths_to_check = [
            ("/", "root"),
            ("/var/lib/postgresql/data", "postgres_data"),
            ("/var/lib/influxdb3", "influxdb_data"),
        ]

        volumes = {}
        for path, name in paths_to_check:
            try:
                usage = shutil.disk_usage(path)
                volumes[name] = {
                    "path": path,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "used_pct": round(usage.used / usage.total * 100, 1),
                }
            except (FileNotFoundError, PermissionError):
                # Path doesn't exist or not accessible in container
                pass

        # At minimum, check root
        if not volumes:
            usage = shutil.disk_usage("/")
            volumes["root"] = {
                "path": "/",
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "used_pct": round(usage.used / usage.total * 100, 1),
            }

        return {"volumes": volumes}
    except Exception as e:
        logger.error("Failed to get disk capacity: %s", e)
        return {"error": str(e)}
```

---

## Verification

```bash
# Restart UI
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Test capacity endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8080/operator/system/capacity
```

Expected response:
```json
{
  "postgres": {
    "db_size_bytes": 1310720000,
    "db_size_mb": 1250.0,
    "connections_used": 15,
    "connections_max": 100,
    "connections_pct": 15.0,
    "top_tables": [
      {"name": "public.telemetry_raw", "total_mb": 450.5, "data_mb": 400.0, "index_mb": 50.5},
      {"name": "public.device_state", "total_mb": 120.3, "data_mb": 100.0, "index_mb": 20.3}
    ]
  },
  "influxdb": {
    "file_limit": 1000,
    "database_count": 5,
    "databases": ["telemetry_enabled", "telemetry_disabled", ...]
  },
  "disk": {
    "volumes": {
      "root": {
        "path": "/",
        "total_gb": 100.0,
        "used_gb": 57.5,
        "free_gb": 42.5,
        "used_pct": 57.5
      }
    }
  }
}
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/system.py` |

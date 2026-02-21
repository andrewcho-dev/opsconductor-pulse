# Task 002 — Sensor Auto-Discovery in Ingestor

## File

Modify `services/ingest_iot/ingest.py`

## Context

When a device sends telemetry, the `metrics` JSONB contains keys like `{"temperature": 22.5, "humidity": 65}`. Each key represents a sensor measurement. If a sensor record doesn't exist for that (device_id, metric_name) pair, we should auto-create one.

The insertion point is in `db_worker()` after line 1291 (after `await self.batch_writer.add(record)`), before the message route fan-out. At this point we have:
- `tenant_id`, `device_id`, `site_id` — validated
- `metrics` dict — `payload.get("metrics", {}) or {}`
- `ts` — event timestamp
- `self.pool` — DB connection pool

## Implementation

### Step 1: Add a sensor cache

Add an in-memory cache to avoid hitting the DB on every message. Similar pattern to `self.auth_cache`.

Near the top of the `IngestService` class `__init__`, add:

```python
# Sensor auto-discovery cache: set of (tenant_id, device_id, metric_name) tuples
# that are known to exist. Avoids DB lookup on every telemetry message.
self._known_sensors: set[tuple[str, str, str]] = set()
```

### Step 2: Add sensor auto-discovery method

Add this method to `IngestService`:

```python
async def _ensure_sensors(self, tenant_id: str, device_id: str, metrics: dict, ts):
    """Auto-discover sensors from telemetry metric keys.

    For each metric key in the payload, ensure a sensor record exists.
    Uses an in-memory cache to avoid DB hits on known sensors.
    Respects the device's sensor_limit.
    """
    if not metrics:
        return

    new_keys = []
    for key in metrics:
        if (tenant_id, device_id, key) not in self._known_sensors:
            new_keys.append(key)

    if not new_keys:
        # All metric keys are already known — just update last_value/last_seen
        try:
            assert self.pool is not None
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await _set_tenant_write_context(conn, tenant_id)
                    for key in metrics:
                        value = metrics[key]
                        if isinstance(value, (int, float)):
                            await conn.execute(
                                """
                                UPDATE sensors SET last_value = $1, last_seen_at = $2, updated_at = now()
                                WHERE tenant_id = $3 AND device_id = $4 AND metric_name = $5
                                """,
                                float(value), ts, tenant_id, device_id, key,
                            )
        except Exception as e:
            logger.debug("sensor_last_value_update_failed: %s", e)
        return

    # Some new keys found — check DB for existing sensors and auto-create missing ones
    try:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await _set_tenant_write_context(conn, tenant_id)

                # Fetch all existing sensors for this device
                existing = await conn.fetch(
                    "SELECT metric_name FROM sensors WHERE tenant_id = $1 AND device_id = $2",
                    tenant_id, device_id,
                )
                existing_names = {row["metric_name"] for row in existing}

                # Cache all existing
                for name in existing_names:
                    self._known_sensors.add((tenant_id, device_id, name))

                # Find truly new metric keys
                to_create = [k for k in new_keys if k not in existing_names]

                if to_create:
                    # Check sensor limit
                    limit_row = await conn.fetchrow(
                        """
                        SELECT dr.sensor_limit, dt.default_sensor_limit
                        FROM device_registry dr
                        LEFT JOIN device_tiers dt ON dt.tier_id = dr.tier_id
                        WHERE dr.tenant_id = $1 AND dr.device_id = $2
                        """,
                        tenant_id, device_id,
                    )
                    effective_limit = 20
                    if limit_row:
                        effective_limit = limit_row["sensor_limit"] or limit_row["default_sensor_limit"] or 20

                    current_count = len(existing_names)
                    available_slots = max(0, effective_limit - current_count)

                    if available_slots == 0:
                        logger.warning(
                            "sensor_limit_reached",
                            extra={
                                "tenant_id": tenant_id,
                                "device_id": device_id,
                                "limit": effective_limit,
                                "new_keys": to_create,
                            },
                        )
                    else:
                        # Create sensors up to the available slots
                        for key in to_create[:available_slots]:
                            sensor_type = _infer_sensor_type(key)
                            unit = _infer_unit(key, sensor_type)
                            value = metrics.get(key)
                            numeric_value = float(value) if isinstance(value, (int, float)) else None

                            await conn.execute(
                                """
                                INSERT INTO sensors (
                                    tenant_id, device_id, metric_name, sensor_type,
                                    label, unit, auto_discovered, last_value, last_seen_at, status
                                ) VALUES ($1, $2, $3, $4, $5, $6, true, $7, $8, 'active')
                                ON CONFLICT (tenant_id, device_id, metric_name) DO NOTHING
                                """,
                                tenant_id, device_id, key, sensor_type,
                                _humanize_metric_name(key), unit,
                                numeric_value, ts,
                            )
                            self._known_sensors.add((tenant_id, device_id, key))
                            logger.info(
                                "sensor_auto_discovered",
                                extra={
                                    "tenant_id": tenant_id,
                                    "device_id": device_id,
                                    "metric_name": key,
                                    "sensor_type": sensor_type,
                                },
                            )

                        if len(to_create) > available_slots:
                            logger.warning(
                                "sensor_limit_partial",
                                extra={
                                    "tenant_id": tenant_id,
                                    "device_id": device_id,
                                    "created": available_slots,
                                    "skipped": to_create[available_slots:],
                                },
                            )

                # Update last_value for all known sensors
                for key in metrics:
                    value = metrics[key]
                    if isinstance(value, (int, float)):
                        await conn.execute(
                            """
                            UPDATE sensors SET last_value = $1, last_seen_at = $2, updated_at = now()
                            WHERE tenant_id = $3 AND device_id = $4 AND metric_name = $5
                            """,
                            float(value), ts, tenant_id, device_id, key,
                        )

    except Exception as e:
        # Sensor auto-discovery failure should NOT block telemetry ingestion
        logger.warning("sensor_autodiscovery_failed: %s", e)
```

### Step 3: Add helper functions

Add these at module level (outside the class):

```python
def _infer_sensor_type(metric_name: str) -> str:
    """Infer sensor type from metric name using common patterns."""
    name = metric_name.lower()
    if "temp" in name:
        return "temperature"
    if "humid" in name:
        return "humidity"
    if "press" in name:
        return "pressure"
    if "vibrat" in name:
        return "vibration"
    if "flow" in name:
        return "flow"
    if "level" in name:
        return "level"
    if "power" in name or "kw" in name or "watt" in name:
        return "power"
    if "volt" in name:
        return "electrical"
    if "current" in name or "amp" in name:
        return "electrical"
    if "battery" in name or "batt" in name:
        return "battery"
    if "speed" in name or "rpm" in name:
        return "speed"
    if "weight" in name or "mass" in name or "load" in name:
        return "weight"
    if "ph" == name or name.startswith("ph_"):
        return "chemical"
    if "co2" in name or "gas" in name or "air" in name:
        return "air_quality"
    return "unknown"


def _infer_unit(metric_name: str, sensor_type: str) -> str | None:
    """Infer measurement unit from metric name and type."""
    name = metric_name.lower()
    unit_hints = {
        "temperature": "°C",
        "humidity": "%RH",
        "pressure": "hPa",
        "vibration": "mm/s",
        "flow": "L/min",
        "level": "%",
        "battery": "%",
    }
    if "pct" in name or "percent" in name:
        return "%"
    if "celsius" in name or "_c" in name:
        return "°C"
    if "fahrenheit" in name or "_f" in name:
        return "°F"
    if "_kw" in name or name.endswith("_kw"):
        return "kW"
    if "volt" in name:
        return "V"
    if "amp" in name or "current" in name:
        return "A"
    return unit_hints.get(sensor_type)


def _humanize_metric_name(metric_name: str) -> str:
    """Convert snake_case metric name to human-readable label."""
    return metric_name.replace("_", " ").title()
```

### Step 4: Call from db_worker

In `db_worker()`, after line 1291 (`await self.batch_writer.add(record)`), add:

```python
                # Sensor auto-discovery
                await self._ensure_sensors(tenant_id, device_id, metrics, ts)
```

Where `metrics` is already available as `payload.get("metrics", {}) or {}` (used on line 1288).

**IMPORTANT:** This call must be fire-and-forget in spirit — if it fails, telemetry still goes through. The method internally catches all exceptions and logs warnings. Telemetry ingestion must NEVER be blocked by sensor auto-discovery failures.

### Step 5: Cache eviction

Add a periodic cache cleanup to prevent unbounded growth. In the `stats_worker()` method (which runs on a periodic loop), add:

```python
# Evict sensor cache every 10 minutes to pick up manual deletions
if self._known_sensors and len(self._known_sensors) > 10000:
    self._known_sensors.clear()
```

Or simpler: clear the whole cache every N iterations of the stats loop.

## Notes

- The `ON CONFLICT DO NOTHING` in the INSERT handles race conditions where multiple messages arrive simultaneously with a new metric key
- `_infer_sensor_type` and `_infer_unit` provide reasonable defaults that the user can override via the sensor update API
- Platform health metrics (rssi, battery_pct, etc.) should NOT be auto-discovered as sensors — they go to `device_health_telemetry`. However, at this stage the ingestor doesn't yet split health vs sensor data. That separation will happen when the payload format is updated to distinguish them. For now, if a device sends `battery` in its metrics JSONB, it will be auto-discovered as a sensor. This is acceptable — users can disable or delete unwanted sensor records.
- The `last_value` update on every message is lightweight (single UPDATE by indexed PK columns) and keeps the sensor list fresh for the UI without querying telemetry

## Verification

```bash
cd services/ingest_iot && python3 -c "from ingest import _infer_sensor_type, _infer_unit, _humanize_metric_name; print(_infer_sensor_type('hvac_supply_temp'), _infer_unit('hvac_supply_temp', 'temperature'), _humanize_metric_name('hvac_supply_temp'))"
# Expected: temperature °C Hvac Supply Temp
```

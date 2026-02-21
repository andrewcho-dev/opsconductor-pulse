# Prompt 002 — Evaluator: Anomaly Detection Loop

Read `services/evaluator_iot/evaluator.py` fully — especially `fetch_tenant_rules()`, the main evaluation loop, and `open_or_update_alert()`.

## Add Anomaly Detection Functions

### Rolling stats query

```python
async def compute_rolling_stats(conn, tenant_id: str, device_id: str,
                                 metric_name: str, window_minutes: int) -> dict | None:
    """
    Compute rolling mean and stddev for a metric over the last window_minutes.
    Returns {"mean": float, "stddev": float, "count": int, "latest": float} or None if insufficient data.
    """
    row = await conn.fetchrow(
        """
        SELECT
            AVG((metrics->>$3)::numeric)    AS mean_val,
            STDDEV((metrics->>$3)::numeric) AS stddev_val,
            COUNT(*)                         AS sample_count,
            (SELECT (metrics->>$3)::numeric
             FROM telemetry
             WHERE tenant_id=$1 AND device_id=$2 AND metrics ? $3
             ORDER BY time DESC LIMIT 1)    AS latest_val
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
          AND time > now() - ($4 || ' minutes')::interval
          AND metrics ? $3
        """,
        tenant_id, device_id, metric_name, str(window_minutes)
    )
    if not row or row["sample_count"] is None or row["sample_count"] < 2:
        return None
    return {
        "mean": float(row["mean_val"]),
        "stddev": float(row["stddev_val"]) if row["stddev_val"] else 0.0,
        "count": int(row["sample_count"]),
        "latest": float(row["latest_val"]) if row["latest_val"] is not None else None,
    }
```

### Z-score check

```python
def compute_z_score(value: float, mean: float, stddev: float) -> float | None:
    """Returns Z-score or None if stddev is 0 (no variation)."""
    if stddev == 0:
        return None
    return abs(value - mean) / stddev
```

### Anomaly evaluation loop

In `fetch_tenant_rules()` (or wherever rules are fetched), also fetch `rule_type='anomaly'` rules with their `conditions` JSONB.

In the main evaluation loop, add a branch for anomaly rules:

```python
for rule in anomaly_rules:
    cfg = rule.get("conditions") or {}
    metric_name   = cfg.get("metric_name")
    window_minutes = int(cfg.get("window_minutes", 60))
    z_threshold   = float(cfg.get("z_threshold", 3.0))
    min_samples   = int(cfg.get("min_samples", 10))

    if not metric_name:
        continue

    stats = await compute_rolling_stats(conn, tenant_id, device_id, metric_name, window_minutes)
    if stats is None or stats["count"] < min_samples or stats["latest"] is None:
        continue  # not enough data

    z = compute_z_score(stats["latest"], stats["mean"], stats["stddev"])
    if z is None or z <= z_threshold:
        continue  # not anomalous

    fp = f"anomaly:{device_id}:{metric_name}"
    summary = (
        f"{metric_name} anomaly on {device_id}: "
        f"value={stats['latest']:.2f}, mean={stats['mean']:.2f}, "
        f"stddev={stats['stddev']:.2f}, z={z:.2f}"
    )
    if not await is_silenced(conn, tenant_id, fp):
        await open_or_update_alert(conn, tenant_id, device_id,
                                   site_id, "ANOMALY", fp,
                                   rule["severity"], 0.0, summary,
                                   {"z_score": z, **stats})
```

## Acceptance Criteria

- [ ] `compute_rolling_stats()` queries TimescaleDB for mean/stddev/count/latest
- [ ] `compute_z_score()` returns abs Z-score or None when stddev=0
- [ ] Anomaly rules evaluated in main loop
- [ ] Alert type `ANOMALY` used in `open_or_update_alert()`
- [ ] Respects `is_silenced()` check
- [ ] `pytest -m unit -v` passes

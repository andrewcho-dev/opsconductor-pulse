# Task 3: Add Max Buffer Size to TimescaleBatchWriter

## Context

`services/shared/ingest_core.py:118-143` defines `TimescaleBatchWriter`. The `self.batch` list is unbounded. If the database is unavailable and flush fails repeatedly, records keep accumulating until the process runs out of memory.

## Actions

1. Read `services/shared/ingest_core.py` in full.

2. Add a `max_buffer_size` parameter to `TimescaleBatchWriter.__init__()`:

```python
class TimescaleBatchWriter:
    def __init__(
        self,
        pool,
        batch_size: int = 500,
        flush_interval_ms: int = 1000,
        max_buffer_size: int = 5000,  # NEW
    ):
        self.max_buffer_size = max_buffer_size
        ...
```

3. In the `add()` or `write()` method (wherever records are appended to `self.batch`), add a buffer overflow check BEFORE appending:

```python
def add(self, record: TelemetryRecord) -> None:
    if len(self.batch) >= self.max_buffer_size:
        # Drop the oldest record to make room — log a warning with metrics
        dropped = self.batch.pop(0)
        logger.warning(
            "batch writer buffer full, dropping oldest record",
            extra={
                "tenant_id": dropped.tenant_id,
                "device_id": dropped.device_id,
                "buffer_size": self.max_buffer_size,
            },
        )
        # Increment a Prometheus counter if one exists for this
        # (check if ingest_dropped_total or similar counter exists in metrics.py)
    self.batch.append(record)
```

4. Check `services/shared/metrics.py` for an existing dropped-records counter. If one exists, increment it. If not, add one:
```python
ingest_records_dropped_total = Counter(
    "ingest_records_dropped_total",
    "Telemetry records dropped due to buffer overflow",
    ["tenant_id"],
)
```

5. Do not change batch flush logic.

## Verification

```bash
grep -n 'max_buffer_size\|buffer.*full\|records_dropped' services/shared/ingest_core.py
# Must show the buffer limit and overflow handling
```

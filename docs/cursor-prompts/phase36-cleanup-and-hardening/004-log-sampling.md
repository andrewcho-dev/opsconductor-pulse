# 004: Log Sampling for Rejected Requests

## Task

Implement log sampling to prevent log flooding from rejected/unknown device requests.

## Problem

Without sampling:
- 1,000 unknown devices × 10 requests/sec = 10,000 log entries/sec
- 5 million+ log entries in hours
- Disk exhaustion, slow queries, hidden legitimate issues

## Solution

Sample rejected request logs at configurable rates:

| Event Type | Sample Rate | Reasoning |
|------------|-------------|-----------|
| Unknown device | 1% | High volume, low value |
| Rate limited (known) | 10% | Medium volume, moderate value |
| Rate limited (unknown) | 1% | High volume, low value |
| Auth failures | 100% | Security relevant |
| Validation errors | 10% | Debugging value |

## Implementation

### 1. Sampled Logger

**File:** `services/ingest_iot/sampled_logger.py` (NEW)

```python
"""
Sampled logging with aggregation for high-volume events.
"""
import logging
import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SamplingConfig:
    """Configuration for a sampled log event type."""
    sample_rate: float  # 0.0 to 1.0
    aggregate_window: float = 60.0  # seconds
    min_severity: int = logging.WARNING


@dataclass
class AggregatedEvent:
    """Tracks aggregated events for periodic summary logging."""
    count: int = 0
    first_seen: float = 0
    last_seen: float = 0
    sample_messages: list = field(default_factory=list)
    max_samples: int = 3  # Keep a few examples


class SampledLogger:
    """
    Logger that samples high-volume events and periodically logs summaries.
    """

    DEFAULT_CONFIGS = {
        'unknown_device': SamplingConfig(sample_rate=0.01, aggregate_window=60),
        'rate_limited_unknown': SamplingConfig(sample_rate=0.01, aggregate_window=60),
        'rate_limited_known': SamplingConfig(sample_rate=0.10, aggregate_window=60),
        'validation_error': SamplingConfig(sample_rate=0.10, aggregate_window=60),
        'auth_failure': SamplingConfig(sample_rate=1.0, aggregate_window=0),  # Log all
        'malformed_request': SamplingConfig(sample_rate=0.05, aggregate_window=60),
    }

    def __init__(self, configs: Optional[Dict[str, SamplingConfig]] = None):
        self.configs = configs or self.DEFAULT_CONFIGS
        self._aggregated: Dict[str, AggregatedEvent] = defaultdict(AggregatedEvent)
        self._lock = threading.Lock()
        self._last_flush = time.time()

        # Start background flush thread
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def log(
        self,
        event_type: str,
        message: str,
        level: int = logging.WARNING,
        extra: Optional[dict] = None,
    ):
        """
        Log an event with sampling.

        Args:
            event_type: Type of event (must be in configs)
            message: Log message
            level: Logging level
            extra: Additional context
        """
        config = self.configs.get(event_type)
        if not config:
            # Unknown event type - log normally
            logger.log(level, message, extra=extra)
            return

        now = time.time()

        with self._lock:
            agg = self._aggregated[event_type]

            # Update aggregation
            agg.count += 1
            if agg.first_seen == 0:
                agg.first_seen = now
            agg.last_seen = now

            # Keep sample messages
            if len(agg.sample_messages) < agg.max_samples:
                agg.sample_messages.append({
                    'message': message,
                    'extra': extra,
                    'time': datetime.utcnow().isoformat(),
                })

        # Sample decision
        if config.sample_rate >= 1.0 or random.random() < config.sample_rate:
            # Log this individual event
            sampled_message = f"[SAMPLED 1/{int(1/config.sample_rate)}] {message}"
            logger.log(level, sampled_message, extra=extra)

    def _flush_loop(self):
        """Background thread to periodically flush aggregated summaries."""
        while not self._stop_event.wait(timeout=30):
            self._flush_aggregated()

    def _flush_aggregated(self):
        """Log summary of aggregated events."""
        now = time.time()
        events_to_flush = []

        with self._lock:
            for event_type, agg in list(self._aggregated.items()):
                config = self.configs.get(event_type)
                if not config:
                    continue

                # Check if window has passed
                if agg.count > 0 and (now - agg.first_seen) >= config.aggregate_window:
                    events_to_flush.append((event_type, agg, config))
                    # Reset aggregation
                    self._aggregated[event_type] = AggregatedEvent()

        # Log summaries outside the lock
        for event_type, agg, config in events_to_flush:
            if agg.count == 0:
                continue

            duration = agg.last_seen - agg.first_seen
            rate = agg.count / duration if duration > 0 else agg.count

            summary = (
                f"[SUMMARY] {event_type}: {agg.count} events "
                f"in {duration:.1f}s ({rate:.1f}/s)"
            )

            # Include sample messages
            if agg.sample_messages:
                samples = "; ".join(m['message'][:100] for m in agg.sample_messages[:2])
                summary += f" | Samples: {samples}"

            logger.warning(summary)

    def get_stats(self) -> Dict[str, dict]:
        """Get current aggregation stats."""
        with self._lock:
            return {
                event_type: {
                    'count': agg.count,
                    'first_seen': agg.first_seen,
                    'last_seen': agg.last_seen,
                }
                for event_type, agg in self._aggregated.items()
            }

    def shutdown(self):
        """Stop background thread and flush remaining."""
        self._stop_event.set()
        self._flush_thread.join(timeout=5)
        self._flush_aggregated()


# Singleton instance
_sampled_logger: Optional[SampledLogger] = None


def get_sampled_logger() -> SampledLogger:
    """Get or create sampled logger instance."""
    global _sampled_logger
    if _sampled_logger is None:
        _sampled_logger = SampledLogger()
    return _sampled_logger
```

### 2. Integration with Ingest Handler

**File:** `services/ingest_iot/ingest.py`

Replace direct logging with sampled logging:

```python
from sampled_logger import get_sampled_logger

sampled_logger = get_sampled_logger()

# In request handler:

async def handle_telemetry(request):
    client_ip = get_client_ip(request)
    device_id = extract_device_id(request)

    # Check if device is known
    is_known = await is_known_device(device_id) if device_id else False

    if not is_known:
        # Log with sampling
        sampled_logger.log(
            'unknown_device',
            f"Unknown device attempted connection: device={device_id}, ip={client_ip}",
            extra={'device_id': device_id, 'ip': client_ip},
        )
        return web.json_response(
            {"error": "unknown_device", "message": "Device not registered"},
            status=403
        )

    # Rate limit check
    allowed, reason, status_code = rate_limiter.check_all(device_id, client_ip, is_known)

    if not allowed:
        event_type = 'rate_limited_known' if is_known else 'rate_limited_unknown'
        sampled_logger.log(
            event_type,
            f"Rate limited: {reason}",
            extra={'device_id': device_id, 'ip': client_ip},
        )
        return web.json_response({"error": "rate_limited"}, status=status_code)

    # Validation
    try:
        data = await parse_telemetry(request)
    except ValidationError as e:
        sampled_logger.log(
            'validation_error',
            f"Invalid telemetry: {e}",
            extra={'device_id': device_id, 'ip': client_ip, 'error': str(e)},
        )
        return web.json_response({"error": "validation_error"}, status=400)

    # Continue with normal processing...
```

### 3. Graceful Shutdown

Ensure logs are flushed on shutdown:

```python
# In main application setup:
import atexit

sampled_logger = get_sampled_logger()

def shutdown_handler():
    sampled_logger.shutdown()

atexit.register(shutdown_handler)

# Or in async cleanup:
async def cleanup():
    get_sampled_logger().shutdown()
```

### 4. Configuration via Environment

```python
import os

def get_sampling_configs_from_env() -> Dict[str, SamplingConfig]:
    """Load sampling configuration from environment variables."""
    return {
        'unknown_device': SamplingConfig(
            sample_rate=float(os.getenv('LOG_SAMPLE_UNKNOWN_DEVICE', '0.01')),
            aggregate_window=float(os.getenv('LOG_AGG_WINDOW', '60')),
        ),
        'rate_limited_unknown': SamplingConfig(
            sample_rate=float(os.getenv('LOG_SAMPLE_RATE_LIMITED_UNKNOWN', '0.01')),
            aggregate_window=float(os.getenv('LOG_AGG_WINDOW', '60')),
        ),
        'rate_limited_known': SamplingConfig(
            sample_rate=float(os.getenv('LOG_SAMPLE_RATE_LIMITED_KNOWN', '0.10')),
            aggregate_window=float(os.getenv('LOG_AGG_WINDOW', '60')),
        ),
        'validation_error': SamplingConfig(
            sample_rate=float(os.getenv('LOG_SAMPLE_VALIDATION', '0.10')),
            aggregate_window=float(os.getenv('LOG_AGG_WINDOW', '60')),
        ),
        'auth_failure': SamplingConfig(
            sample_rate=1.0,  # Always log auth failures
            aggregate_window=0,
        ),
    }
```

### 5. Stats Endpoint

Add endpoint to monitor sampling stats:

```python
async def handle_sampling_stats(request):
    """Return log sampling statistics."""
    sampled_logger = get_sampled_logger()
    stats = sampled_logger.get_stats()

    return web.json_response({
        "sampling_stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    })

# Add to routes:
# app.router.add_get('/metrics/log-sampling', handle_sampling_stats)
```

## Example Log Output

Individual sampled log:
```
2024-01-15 10:30:45 WARNING [SAMPLED 1/100] Unknown device attempted connection: device=FAKE-001, ip=192.168.1.100
```

Aggregated summary (every 60 seconds):
```
2024-01-15 10:31:45 WARNING [SUMMARY] unknown_device: 4523 events in 60.0s (75.4/s) | Samples: Unknown device attempted connection: device=FAKE-001; Unknown device attempted connection: device=FAKE-002
```

## Verification

```bash
# Simulate high-volume unknown device requests
for i in {1..1000}; do
  curl -s -X POST https://localhost/ingest/telemetry \
    -H "Content-Type: application/json" \
    -d "{\"device_id\": \"UNKNOWN-$i\", \"data\": {}}" &
done
wait

# Check logs - should see sampled entries, not 1000
docker compose logs --tail=50 ingest_iot

# Check sampling stats
curl https://localhost/ingest/metrics/log-sampling

# Wait 60 seconds for summary
sleep 65
docker compose logs --tail=10 ingest_iot | grep SUMMARY
```

## Files Created/Modified

- `services/ingest_iot/sampled_logger.py` (NEW)
- `services/ingest_iot/ingest.py` (MODIFIED)

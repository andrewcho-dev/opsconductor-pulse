# 003: Rate Limiting for Ingest Endpoint

## Task

Add rate limiting to the ingest endpoint to prevent DoS from unknown/rejected devices.

## Rate Limiting Strategy

| Layer | Limit | Window | Action |
|-------|-------|--------|--------|
| Per device_id | 2 requests | 1 second | 429, no log |
| Per IP (known devices) | 200 requests | 1 second | 429, minimal log |
| Per IP (unknown devices) | 10 requests | 1 minute | 429, sampled log |
| Global | 10,000 requests | 1 second | 503, alert |

## Implementation

### 1. Rate Limiter Module

**File:** `services/ingest_iot/rate_limiter.py` (NEW)

```python
"""
Rate limiter for ingest endpoint using sliding window algorithm.
Uses in-memory storage with automatic cleanup.
"""
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    requests: int  # Number of requests allowed
    window_seconds: float  # Time window in seconds
    log_rejections: bool = True  # Whether to log rejections
    log_sample_rate: float = 1.0  # 1.0 = log all, 0.01 = log 1%


@dataclass
class SlidingWindow:
    """Sliding window counter for rate limiting."""
    timestamps: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_request(self, now: float, window_seconds: float, max_requests: int) -> Tuple[bool, int]:
        """
        Add a request and check if within limit.
        Returns (allowed, current_count).
        """
        with self.lock:
            # Remove expired timestamps
            cutoff = now - window_seconds
            self.timestamps = [ts for ts in self.timestamps if ts > cutoff]

            current_count = len(self.timestamps)

            if current_count >= max_requests:
                return False, current_count

            self.timestamps.append(now)
            return True, current_count + 1


class RateLimiter:
    """Multi-layer rate limiter with automatic cleanup."""

    def __init__(self):
        # Separate windows for different key types
        self._device_windows: Dict[str, SlidingWindow] = defaultdict(SlidingWindow)
        self._ip_windows: Dict[str, SlidingWindow] = defaultdict(SlidingWindow)
        self._unknown_ip_windows: Dict[str, SlidingWindow] = defaultdict(SlidingWindow)

        # Global counter
        self._global_window = SlidingWindow()

        # Configuration
        self.config = {
            'device': RateLimitConfig(
                requests=2,
                window_seconds=1.0,
                log_rejections=False,  # Too noisy
            ),
            'ip_known': RateLimitConfig(
                requests=200,
                window_seconds=1.0,
                log_rejections=True,
                log_sample_rate=0.1,  # Log 10%
            ),
            'ip_unknown': RateLimitConfig(
                requests=10,
                window_seconds=60.0,
                log_rejections=True,
                log_sample_rate=0.01,  # Log 1%
            ),
            'global': RateLimitConfig(
                requests=10000,
                window_seconds=1.0,
                log_rejections=True,
            ),
        }

        # Cleanup thread
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()
        self._cleanup_lock = threading.Lock()

        # Stats
        self._stats = defaultdict(int)
        self._stats_lock = threading.Lock()

    def check_device_limit(self, device_id: str) -> Tuple[bool, str]:
        """Check per-device rate limit."""
        cfg = self.config['device']
        window = self._device_windows[device_id]
        allowed, count = window.add_request(time.time(), cfg.window_seconds, cfg.requests)

        if not allowed:
            self._increment_stat('device_limited')
            return False, f"Device {device_id} rate limited ({count}/{cfg.requests} per {cfg.window_seconds}s)"

        return True, ""

    def check_ip_limit(self, ip: str, is_known_device: bool) -> Tuple[bool, str]:
        """Check per-IP rate limit."""
        if is_known_device:
            cfg = self.config['ip_known']
            window = self._ip_windows[ip]
            stat_key = 'ip_known_limited'
        else:
            cfg = self.config['ip_unknown']
            window = self._unknown_ip_windows[ip]
            stat_key = 'ip_unknown_limited'

        allowed, count = window.add_request(time.time(), cfg.window_seconds, cfg.requests)

        if not allowed:
            self._increment_stat(stat_key)
            return False, f"IP {ip} rate limited ({count}/{cfg.requests} per {cfg.window_seconds}s)"

        return True, ""

    def check_global_limit(self) -> Tuple[bool, str]:
        """Check global rate limit."""
        cfg = self.config['global']
        allowed, count = self._global_window.add_request(
            time.time(), cfg.window_seconds, cfg.requests
        )

        if not allowed:
            self._increment_stat('global_limited')
            logger.warning(f"Global rate limit reached: {count}/{cfg.requests}")
            return False, "Service temporarily unavailable"

        return True, ""

    def check_all(
        self,
        device_id: Optional[str],
        ip: str,
        is_known_device: bool
    ) -> Tuple[bool, str, int]:
        """
        Check all rate limits.
        Returns (allowed, reason, http_status_code).
        """
        self._maybe_cleanup()

        # Global limit first (fastest rejection)
        allowed, reason = self.check_global_limit()
        if not allowed:
            return False, reason, 503

        # IP limit for unknown devices (before device check)
        if not is_known_device:
            allowed, reason = self.check_ip_limit(ip, is_known_device=False)
            if not allowed:
                return False, reason, 429

        # Device limit (only for known devices)
        if device_id and is_known_device:
            allowed, reason = self.check_device_limit(device_id)
            if not allowed:
                return False, reason, 429

            # IP limit for known devices
            allowed, reason = self.check_ip_limit(ip, is_known_device=True)
            if not allowed:
                return False, reason, 429

        self._increment_stat('allowed')
        return True, "", 200

    def should_log_rejection(self, limit_type: str) -> bool:
        """Determine if this rejection should be logged (sampling)."""
        cfg = self.config.get(limit_type)
        if not cfg or not cfg.log_rejections:
            return False

        if cfg.log_sample_rate >= 1.0:
            return True

        import random
        return random.random() < cfg.log_sample_rate

    def get_stats(self) -> Dict[str, int]:
        """Get rate limiting statistics."""
        with self._stats_lock:
            return dict(self._stats)

    def reset_stats(self):
        """Reset statistics."""
        with self._stats_lock:
            self._stats.clear()

    def _increment_stat(self, key: str):
        with self._stats_lock:
            self._stats[key] += 1

    def _maybe_cleanup(self):
        """Periodically clean up old entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        with self._cleanup_lock:
            if now - self._last_cleanup < self._cleanup_interval:
                return  # Double-check after acquiring lock

            self._last_cleanup = now

            # Clean up windows with no recent activity
            cutoff = now - 300  # 5 minutes

            for windows_dict in [
                self._device_windows,
                self._ip_windows,
                self._unknown_ip_windows
            ]:
                keys_to_remove = []
                for key, window in windows_dict.items():
                    with window.lock:
                        if not window.timestamps or max(window.timestamps) < cutoff:
                            keys_to_remove.append(key)

                for key in keys_to_remove:
                    del windows_dict[key]

            logger.debug(f"Rate limiter cleanup complete")


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
```

### 2. Integrate into Ingest Handler

**File:** `services/ingest_iot/ingest.py`

Add rate limiting at the start of request handling:

```python
from rate_limiter import get_rate_limiter
import logging

logger = logging.getLogger(__name__)

# Add to request handler (early in the function):

async def handle_telemetry(request):
    """Handle incoming telemetry with rate limiting."""
    rate_limiter = get_rate_limiter()

    # Extract identifiers
    client_ip = get_client_ip(request)
    device_id = extract_device_id(request)  # May be None for malformed requests

    # Quick check: is this a known device?
    is_known = await is_known_device(device_id) if device_id else False

    # Apply rate limiting
    allowed, reason, status_code = rate_limiter.check_all(
        device_id=device_id,
        ip=client_ip,
        is_known_device=is_known,
    )

    if not allowed:
        # Determine if we should log this rejection
        if not is_known and rate_limiter.should_log_rejection('ip_unknown'):
            logger.warning(f"Rate limited unknown device: ip={client_ip}, device={device_id}")
        elif is_known and rate_limiter.should_log_rejection('ip_known'):
            logger.info(f"Rate limited known device: ip={client_ip}, device={device_id}")

        return web.json_response(
            {"error": "rate_limited", "message": reason},
            status=status_code
        )

    # Continue with normal processing...
    # ... rest of handler


def get_client_ip(request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (from nginx/load balancer)
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(',')[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get('X-Real-IP', '')
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    peername = request.transport.get_extra_info('peername')
    if peername:
        return peername[0]

    return 'unknown'


# Cache for known devices (refresh periodically)
_known_devices_cache: set = set()
_cache_refresh_time: float = 0
CACHE_TTL = 60  # seconds


async def is_known_device(device_id: str) -> bool:
    """Check if device is registered (with caching)."""
    global _known_devices_cache, _cache_refresh_time

    import time
    now = time.time()

    # Refresh cache if stale
    if now - _cache_refresh_time > CACHE_TTL:
        try:
            # Fetch all device IDs from database
            _known_devices_cache = await fetch_all_device_ids()
            _cache_refresh_time = now
        except Exception as e:
            logger.error(f"Failed to refresh device cache: {e}")
            # Use stale cache on error

    return device_id in _known_devices_cache
```

### 3. Stats Endpoint

**File:** `services/ingest_iot/ingest.py`

Add endpoint to monitor rate limiting:

```python
async def handle_rate_limit_stats(request):
    """Return rate limiting statistics."""
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats()

    return web.json_response({
        "rate_limit_stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    })


# Add to routes:
# app.router.add_get('/metrics/rate-limits', handle_rate_limit_stats)
```

### 4. Prometheus Metrics (Optional)

If using Prometheus, add metrics:

```python
from prometheus_client import Counter, Gauge

# Rate limit metrics
rate_limit_total = Counter(
    'ingest_rate_limit_total',
    'Total rate limited requests',
    ['type']  # device, ip_known, ip_unknown, global
)

rate_limit_allowed = Counter(
    'ingest_requests_allowed_total',
    'Total allowed requests'
)

# Update in rate limiter:
def _increment_stat(self, key: str):
    with self._stats_lock:
        self._stats[key] += 1

    # Prometheus
    if key == 'allowed':
        rate_limit_allowed.inc()
    else:
        rate_limit_total.labels(type=key.replace('_limited', '')).inc()
```

## Configuration via Environment

```python
# In rate_limiter.py, add configuration from environment:
import os

def get_config_from_env() -> dict:
    return {
        'device': RateLimitConfig(
            requests=int(os.getenv('RATE_LIMIT_DEVICE_REQUESTS', '2')),
            window_seconds=float(os.getenv('RATE_LIMIT_DEVICE_WINDOW', '1.0')),
            log_rejections=False,
        ),
        'ip_known': RateLimitConfig(
            requests=int(os.getenv('RATE_LIMIT_IP_KNOWN_REQUESTS', '200')),
            window_seconds=float(os.getenv('RATE_LIMIT_IP_KNOWN_WINDOW', '1.0')),
            log_rejections=True,
            log_sample_rate=0.1,
        ),
        'ip_unknown': RateLimitConfig(
            requests=int(os.getenv('RATE_LIMIT_IP_UNKNOWN_REQUESTS', '10')),
            window_seconds=float(os.getenv('RATE_LIMIT_IP_UNKNOWN_WINDOW', '60.0')),
            log_rejections=True,
            log_sample_rate=0.01,
        ),
        'global': RateLimitConfig(
            requests=int(os.getenv('RATE_LIMIT_GLOBAL_REQUESTS', '10000')),
            window_seconds=float(os.getenv('RATE_LIMIT_GLOBAL_WINDOW', '1.0')),
            log_rejections=True,
        ),
    }
```

## Nginx Layer (Additional Protection)

Add to nginx config for defense in depth:

**File:** `nginx/nginx.conf`

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=ingest_per_ip:10m rate=100r/s;
limit_req_zone $server_name zone=ingest_global:1m rate=10000r/s;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;

server {
    # ... existing config ...

    location /ingest/ {
        # Rate limiting
        limit_req zone=ingest_per_ip burst=50 nodelay;
        limit_req zone=ingest_global burst=1000 nodelay;
        limit_req_status 429;

        # Connection limiting
        limit_conn conn_per_ip 50;
        limit_conn_status 429;

        # Pass to backend
        proxy_pass http://ingest_iot:8080;
        # ... other proxy settings ...
    }
}
```

## Verification

```bash
# Test rate limiting with curl
for i in {1..20}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://localhost/ingest/telemetry \
    -H "Content-Type: application/json" \
    -d '{"device_id": "test-001", "data": {}}'
done

# Expected: First few 200s, then 429s

# Check stats endpoint
curl https://localhost/ingest/metrics/rate-limits

# Load test
ab -n 1000 -c 50 -p payload.json -T application/json \
  https://localhost/ingest/telemetry

# Monitor during test
watch -n 1 'curl -s https://localhost/ingest/metrics/rate-limits | jq .'
```

## Files Created/Modified

- `services/ingest_iot/rate_limiter.py` (NEW)
- `services/ingest_iot/ingest.py` (MODIFIED)
- `nginx/nginx.conf` (MODIFIED - optional)

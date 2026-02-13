"""
Rate limiter for ingest endpoint using sliding window algorithm.
Uses in-memory storage with automatic cleanup.
"""
import os
import random
import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    requests: int
    window_seconds: float
    log_rejections: bool = True
    log_sample_rate: float = 1.0


@dataclass
class SlidingWindow:
    """Sliding window counter for rate limiting."""
    timestamps: list = None
    lock: threading.Lock = None

    def __post_init__(self):
        if self.timestamps is None:
            self.timestamps = []
        if self.lock is None:
            self.lock = threading.Lock()

    def add_request(
        self, now: float, window_seconds: float, max_requests: int
    ) -> Tuple[bool, int]:
        """
        Add a request and check if within limit.
        Returns (allowed, current_count).
        """
        with self.lock:
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
        self._device_windows: Dict[str, SlidingWindow] = defaultdict(
            lambda: SlidingWindow()
        )
        self._ip_windows: Dict[str, SlidingWindow] = defaultdict(
            lambda: SlidingWindow()
        )
        self._unknown_ip_windows: Dict[str, SlidingWindow] = defaultdict(
            lambda: SlidingWindow()
        )
        self._global_window = SlidingWindow()

        self.config = {
            "device": RateLimitConfig(
                requests=int(os.getenv("RATE_LIMIT_DEVICE_REQUESTS", "2")),
                window_seconds=float(os.getenv("RATE_LIMIT_DEVICE_WINDOW", "1.0")),
                log_rejections=False,
            ),
            "ip_known": RateLimitConfig(
                requests=int(os.getenv("RATE_LIMIT_IP_KNOWN_REQUESTS", "200")),
                window_seconds=float(os.getenv("RATE_LIMIT_IP_KNOWN_WINDOW", "1.0")),
                log_rejections=True,
                log_sample_rate=0.1,
            ),
            "ip_unknown": RateLimitConfig(
                requests=int(os.getenv("RATE_LIMIT_IP_UNKNOWN_REQUESTS", "10")),
                window_seconds=float(
                    os.getenv("RATE_LIMIT_IP_UNKNOWN_WINDOW", "60.0")
                ),
                log_rejections=True,
                log_sample_rate=0.01,
            ),
            "global": RateLimitConfig(
                requests=int(os.getenv("RATE_LIMIT_GLOBAL_REQUESTS", "10000")),
                window_seconds=float(os.getenv("RATE_LIMIT_GLOBAL_WINDOW", "1.0")),
                log_rejections=True,
            ),
        }

        self._cleanup_interval = 60
        self._last_cleanup = time.time()
        self._cleanup_lock = threading.Lock()
        self._stats: Dict[str, int] = defaultdict(int)
        self._stats_lock = threading.Lock()

    def check_device_limit(self, device_id: str) -> Tuple[bool, str]:
        cfg = self.config["device"]
        window = self._device_windows[device_id]
        allowed, count = window.add_request(
            time.time(), cfg.window_seconds, cfg.requests
        )
        if not allowed:
            self._increment_stat("device_limited")
            return False, (
                f"Device {device_id} rate limited "
                f"({count}/{cfg.requests} per {cfg.window_seconds}s)"
            )
        return True, ""

    def check_ip_limit(
        self, ip: str, is_known_device: bool
    ) -> Tuple[bool, str]:
        if is_known_device:
            cfg = self.config["ip_known"]
            window = self._ip_windows[ip]
            stat_key = "ip_known_limited"
        else:
            cfg = self.config["ip_unknown"]
            window = self._unknown_ip_windows[ip]
            stat_key = "ip_unknown_limited"
        allowed, count = window.add_request(
            time.time(), cfg.window_seconds, cfg.requests
        )
        if not allowed:
            self._increment_stat(stat_key)
            return False, (
                f"IP {ip} rate limited "
                f"({count}/{cfg.requests} per {cfg.window_seconds}s)"
            )
        return True, ""

    def check_global_limit(self) -> Tuple[bool, str]:
        cfg = self.config["global"]
        allowed, count = self._global_window.add_request(
            time.time(), cfg.window_seconds, cfg.requests
        )
        if not allowed:
            self._increment_stat("global_limited")
            logger.warning(
                "Global rate limit reached: %s/%s", count, cfg.requests
            )
            return False, "Service temporarily unavailable"
        return True, ""

    def check_all(
        self,
        device_id: Optional[str],
        ip: str,
        is_known_device: bool,
    ) -> Tuple[bool, str, int]:
        """
        Check all rate limits.
        Returns (allowed, reason, http_status_code).
        """
        self._maybe_cleanup()

        allowed, reason = self.check_global_limit()
        if not allowed:
            return False, reason, 503

        if not is_known_device:
            allowed, reason = self.check_ip_limit(ip, is_known_device=False)
            if not allowed:
                return False, reason, 429

        if device_id and is_known_device:
            allowed, reason = self.check_device_limit(device_id)
            if not allowed:
                return False, reason, 429
            allowed, reason = self.check_ip_limit(ip, is_known_device=True)
            if not allowed:
                return False, reason, 429

        self._increment_stat("allowed")
        return True, "", 200

    def should_log_rejection(self, limit_type: str) -> bool:
        cfg = self.config.get(limit_type)
        if not cfg or not cfg.log_rejections:
            return False
        if cfg.log_sample_rate >= 1.0:
            return True
        return random.random() < cfg.log_sample_rate

    def get_stats(self) -> Dict[str, int]:
        with self._stats_lock:
            return dict(self._stats)

    def _increment_stat(self, key: str) -> None:
        with self._stats_lock:
            self._stats[key] += 1

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        with self._cleanup_lock:
            if now - self._last_cleanup < self._cleanup_interval:
                return
            self._last_cleanup = now
            cutoff = now - 300
            for d in (
                self._device_windows,
                self._ip_windows,
                self._unknown_ip_windows,
            ):
                to_remove = [
                    k
                    for k, w in list(d.items())
                    if not w.timestamps or max(w.timestamps) < cutoff
                ]
                for k in to_remove:
                    del d[k]
            logger.debug("Rate limiter cleanup complete")


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

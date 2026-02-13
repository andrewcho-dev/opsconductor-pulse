"""
Sampled logging with aggregation for high-volume events.
"""
import logging
import os
import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SamplingConfig:
    """Configuration for a sampled log event type."""
    sample_rate: float
    aggregate_window: float = 60.0
    min_severity: int = logging.WARNING


@dataclass
class AggregatedEvent:
    """Tracks aggregated events for periodic summary logging."""
    count: int = 0
    first_seen: float = 0
    last_seen: float = 0
    sample_messages: list = field(default_factory=list)
    max_samples: int = 3


class SampledLogger:
    """
    Logger that samples high-volume events and periodically logs summaries.
    """

    DEFAULT_CONFIGS = {
        "unknown_device": SamplingConfig(sample_rate=0.01, aggregate_window=60),
        "rate_limited_unknown": SamplingConfig(sample_rate=0.01, aggregate_window=60),
        "rate_limited_known": SamplingConfig(sample_rate=0.10, aggregate_window=60),
        "validation_error": SamplingConfig(sample_rate=0.10, aggregate_window=60),
        "auth_failure": SamplingConfig(sample_rate=1.0, aggregate_window=0),
        "malformed_request": SamplingConfig(sample_rate=0.05, aggregate_window=60),
    }

    def __init__(self, configs: Optional[Dict[str, SamplingConfig]] = None):
        self.configs = configs or self._configs_from_env()
        self._aggregated: Dict[str, AggregatedEvent] = defaultdict(AggregatedEvent)
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def _configs_from_env(self) -> Dict[str, SamplingConfig]:
        rate = float(os.getenv("LOG_SAMPLE_UNKNOWN_DEVICE", "0.01"))
        window = float(os.getenv("LOG_AGG_WINDOW", "60"))
        return {
            "unknown_device": SamplingConfig(sample_rate=rate, aggregate_window=window),
            "rate_limited_unknown": SamplingConfig(
                sample_rate=float(os.getenv("LOG_SAMPLE_RATE_LIMITED_UNKNOWN", "0.01")),
                aggregate_window=window,
            ),
            "rate_limited_known": SamplingConfig(
                sample_rate=float(os.getenv("LOG_SAMPLE_RATE_LIMITED_KNOWN", "0.10")),
                aggregate_window=window,
            ),
            "validation_error": SamplingConfig(
                sample_rate=float(os.getenv("LOG_SAMPLE_VALIDATION", "0.10")),
                aggregate_window=window,
            ),
            "auth_failure": SamplingConfig(sample_rate=1.0, aggregate_window=0),
            "malformed_request": SamplingConfig(
                sample_rate=0.05, aggregate_window=window
            ),
        }

    def log(
        self,
        event_type: str,
        message: str,
        level: int = logging.WARNING,
        extra: Optional[dict] = None,
    ) -> None:
        config = self.configs.get(event_type)
        if not config:
            logger.log(level, message, extra=extra)
            return

        now = time.time()
        with self._lock:
            agg = self._aggregated[event_type]
            agg.count += 1
            if agg.first_seen == 0:
                agg.first_seen = now
            agg.last_seen = now
            if len(agg.sample_messages) < agg.max_samples:
                agg.sample_messages.append({
                    "message": message,
                    "extra": extra,
                    "time": datetime.utcnow().isoformat(),
                })

        if config.sample_rate >= 1.0 or random.random() < config.sample_rate:
            label = f"[SAMPLED 1/{int(1 / config.sample_rate)}]" if config.sample_rate < 1.0 else ""
            logger.log(level, f"{label} {message}".strip(), extra=extra)

    def _flush_loop(self) -> None:
        while not self._stop_event.wait(timeout=30):
            self._flush_aggregated()

    def _flush_aggregated(self) -> None:
        now = time.time()
        to_flush = []
        with self._lock:
            for event_type, agg in list(self._aggregated.items()):
                config = self.configs.get(event_type)
                if not config or agg.count == 0:
                    continue
                if (now - agg.first_seen) >= config.aggregate_window:
                    to_flush.append((event_type, agg, config))
                    self._aggregated[event_type] = AggregatedEvent()
        for event_type, agg, config in to_flush:
            duration = agg.last_seen - agg.first_seen
            rate = agg.count / duration if duration > 0 else agg.count
            summary = (
                f"[SUMMARY] {event_type}: {agg.count} events "
                f"in {duration:.1f}s ({rate:.1f}/s)"
            )
            if agg.sample_messages:
                samples = "; ".join(
                    m["message"][:100] for m in agg.sample_messages[:2]
                )
                summary += f" | Samples: {samples}"
            logger.warning(summary)

    def get_stats(self) -> Dict[str, dict]:
        with self._lock:
            return {
                k: {
                    "count": v.count,
                    "first_seen": v.first_seen,
                    "last_seen": v.last_seen,
                }
                for k, v in self._aggregated.items()
            }

    def shutdown(self) -> None:
        self._stop_event.set()
        self._flush_thread.join(timeout=5)
        self._flush_aggregated()


_sampled_logger: Optional[SampledLogger] = None


def get_sampled_logger() -> SampledLogger:
    global _sampled_logger
    if _sampled_logger is None:
        _sampled_logger = SampledLogger()
    return _sampled_logger

"""MQTT topic matching with + and # wildcards.

+ matches exactly one topic level.
# matches zero or more remaining levels (must be last segment).

Examples:
    mqtt_topic_matches("tenant/+/device/+/telemetry", "tenant/T1/device/D1/telemetry")   -> True
    mqtt_topic_matches("tenant/+/device/#", "tenant/T1/device/D1/telemetry")              -> True
    mqtt_topic_matches("tenant/T1/device/D1/telemetry", "tenant/T2/device/D1/telemetry")  -> False
"""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=1024)
def _compile_topic_regex(topic_filter: str) -> re.Pattern:
    """Convert MQTT topic filter to compiled regex.

    + -> [^/]+    (one level)
    # -> .*       (zero or more levels, must be last)
    """
    parts = topic_filter.split("/")
    regex_parts: list[str] = []
    for part in parts:
        if part == "+":
            regex_parts.append("[^/]+")
        elif part == "#":
            regex_parts.append(".*")
            break
        else:
            regex_parts.append(re.escape(part))
    pattern = "^" + "/".join(regex_parts) + "$"
    return re.compile(pattern)


def mqtt_topic_matches(topic_filter: str, topic: str) -> bool:
    """Check if an MQTT topic matches a topic filter with wildcards."""
    regex = _compile_topic_regex(topic_filter)
    return regex.match(topic) is not None


def evaluate_payload_filter(filter_spec: dict, payload: dict) -> bool:
    """Evaluate a simple payload filter against a message payload.

    Supports operators at the top level of the filter_spec:
        {"temperature": {"$gt": 80}}                -> payload["metrics"]["temperature"] > 80
        {"humidity": {"$lt": 50}}                   -> payload["metrics"]["humidity"] < 50
        {"temperature": {"$gte": 70, "$lte": 100}}  -> range check
        {"device_type": "sensor"}                   -> exact match on payload field

    Looks for values in payload["metrics"] first, then payload root.
    All conditions must match (AND logic).
    """
    if not filter_spec:
        return True

    metrics = payload.get("metrics", {}) or {}

    for key, condition in filter_spec.items():
        value = metrics.get(key)
        if value is None:
            value = payload.get(key)
        if value is None:
            return False

        if isinstance(condition, dict):
            for op, threshold in condition.items():
                try:
                    value_num = float(value)
                    threshold_num = float(threshold)
                except (TypeError, ValueError):
                    return False

                if op == "$gt" and not (value_num > threshold_num):
                    return False
                elif op == "$gte" and not (value_num >= threshold_num):
                    return False
                elif op == "$lt" and not (value_num < threshold_num):
                    return False
                elif op == "$lte" and not (value_num <= threshold_num):
                    return False
                elif op == "$eq" and not (value_num == threshold_num):
                    return False
                elif op == "$ne" and not (value_num != threshold_num):
                    return False
        else:
            if str(value) != str(condition):
                return False

    return True


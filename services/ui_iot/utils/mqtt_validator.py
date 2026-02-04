"""MQTT integration validation."""

import re
from dataclasses import dataclass
from typing import Optional

ALLOWED_TEMPLATE_VARS = {
    "tenant_id",
    "severity",
    "site_id",
    "device_id",
    "alert_id",
    "alert_type",
}


@dataclass
class MQTTValidationResult:
    """Result of MQTT topic validation."""

    valid: bool
    error: Optional[str] = None


def validate_mqtt_topic(topic: str, tenant_id: str) -> MQTTValidationResult:
    """Validate an MQTT topic template."""
    if not topic or not topic.strip():
        return MQTTValidationResult(valid=False, error="Topic is empty")

    topic = topic.strip()

    if len(topic) > 512:
        return MQTTValidationResult(valid=False, error="Topic is too long")

    if "\0" in topic:
        return MQTTValidationResult(valid=False, error="Topic contains null character")

    if "+" in topic or "#" in topic:
        return MQTTValidationResult(valid=False, error="MQTT wildcards are not allowed")

    if not topic.startswith("alerts/"):
        return MQTTValidationResult(valid=False, error="Topic must start with alerts/")

    if "{" in topic or "}" in topic:
        variables = re.findall(r"\{([^{}]+)\}", topic)
        if not variables:
            return MQTTValidationResult(valid=False, error="Invalid template variables")

        unknown = sorted({var for var in variables if var not in ALLOWED_TEMPLATE_VARS})
        if unknown:
            return MQTTValidationResult(
                valid=False,
                error=f"Unknown template variables: {', '.join(unknown)}",
            )

        stripped = re.sub(r"\{[^{}]+\}", "", topic)
        if "{" in stripped or "}" in stripped:
            return MQTTValidationResult(valid=False, error="Invalid template variables")

    return MQTTValidationResult(valid=True)

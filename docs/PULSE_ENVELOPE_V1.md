# Pulse Envelope v1 - Specification

**Version:** 1
**Status:** Stable
**Effective:** 2026-02-14

---

## Overview

The Pulse Envelope is the canonical payload format for all telemetry ingested by
OpsConductor-Pulse. Every message - whether delivered over MQTT or HTTP - must conform
to this schema. Messages that fail validation are written to `quarantine_events` with
a rejection reason and are never written to the telemetry hypertable.

---

## Transport

### MQTT
- **Broker:** Mosquitto on port 1883 (TCP) or 9001 (WebSocket)
- **Topic convention:** `tenant/{tenant_id}/device/{device_id}/{msg_type}`
- **QoS:** 0 or 1 (QoS 2 not recommended for high-frequency telemetry)
- **Payload encoding:** UTF-8 JSON

### HTTP
- **Endpoint:** `POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}`
- **Content-Type:** `application/json`
- **Authentication:** `X-Provision-Token: {token}` header

---

## Envelope Schema (v1)

```json
{
  "version": "1",
  "ts": 1700000000.000,
  "site_id": "site-abc",
  "seq": 42,
  "metrics": {
    "temp_c": 25.4,
    "humidity_pct": 61.2,
    "battery_v": 3.7
  },
  "lat": 37.7749,
  "lng": -122.4194,
  "provision_token": "tok-xxxxxxxxxxxxxxxx"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | No (defaults to `"1"`) | Envelope version. Must be `"1"`. Unknown versions are rejected. |
| `ts` | float | **Yes** | Unix timestamp (seconds, UTC). Must not be more than 60s in the future. |
| `site_id` | string | No | Site identifier. Must match a registered site for this tenant if provided. |
| `seq` | integer | No | Monotonically increasing sequence number. Used for out-of-order detection. |
| `metrics` | object | No | Key-value pairs of metric readings. Keys are raw metric names. Values are numbers. |
| `lat` | float | No | Device GPS latitude (-90 to 90). |
| `lng` | float | No | Device GPS longitude (-180 to 180). |
| `provision_token` | string | **Yes** (MQTT) | Device authentication token issued at provisioning. Required for MQTT ingestion. Validated against SHA-256 hash stored in `device_state`. |

`tenant_id` and `device_id` are extracted from the MQTT topic or HTTP path - they are
**not** fields in the envelope payload.

---

## Validation Rules

Envelopes that fail any rule are written to `quarantine_events` with a `rejection_reason`:

| Rule | Rejection reason |
|------|-----------------|
| `ts` missing | `missing_timestamp` |
| `ts` more than 60s in future | `future_timestamp` |
| `ts` more than 30 days in past | `stale_timestamp` |
| `provision_token` invalid | `invalid_token` |
| `version` not in supported set | `unsupported_envelope_version:{v}` |
| `metrics` values are not numbers | `invalid_metric_value` |
| Device not registered | `device_not_found` |
| Subscription suspended | `subscription_suspended` |

---

## Metric normalization

Raw metric values in the envelope are normalized before storage using the `metric_mappings`
table:

```
stored_value = raw_value * multiplier + offset
```

If no mapping exists for a metric name, the raw value is stored unchanged.

---

## Forward compatibility

v1 envelopes are forwards-compatible under these rules:

- **Additive fields are safe.** Devices may include additional fields not listed above.
  Unknown fields are ignored by the ingest pipeline.
- **Version bump required for:** removing required fields, changing field semantics,
  changing topic convention, changing auth mechanism.
- **Version `"2"` will be announced** with a migration guide and a minimum 90-day
  parallel support window before v1 is deprecated.

---

## Example: Minimal valid envelope

```json
{
  "ts": 1700000000.0,
  "provision_token": "tok-abc123",
  "metrics": {"temp_c": 22.5}
}
```

## Example: Full envelope

```json
{
  "version": "1",
  "ts": 1700000000.0,
  "site_id": "site-warehouse-a",
  "seq": 1042,
  "metrics": {
    "temp_c": 22.5,
    "humidity_pct": 55.0,
    "co2_ppm": 412.0,
    "battery_v": 3.8
  },
  "lat": 37.7749,
  "lng": -122.4194,
  "provision_token": "tok-abc123"
}
```

# Prompt 005 — Write Pulse Envelope v1 Spec Document

## Context

The Pulse ingest envelope is now versioned (prompt 004). We need a durable spec document that serves as the contract between devices and the platform. This document is the reference for device firmware developers, integration partners, and future engineers.

## Your Task

Create the file `docs/specs/pulse-envelope-v1.md` with the following sections:

### Required sections:

**1. Overview**
- What the Pulse Envelope is
- Who uses it (devices publishing telemetry)
- Transport methods: MQTT and HTTP POST

**2. MQTT Transport**
- Topic convention: `tenant/{tenant_id}/device/{device_id}/{msg_type}`
- Valid `msg_type` values and what they mean
- QoS recommendations
- Authentication: provision token in payload (not MQTT username/password)

**3. HTTP Transport**
- Endpoint: `POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}`
- Authentication: provision token in payload body
- Content-Type: `application/json`

**4. Payload Schema**
Document every field from `validate_and_prepare()` in `services/shared/ingest_core.py`:

```json
{
  "version": "1",          // string, optional, defaults to "1"
  "ts": 1700000000,        // unix timestamp (integer, seconds), required
  "site_id": "uuid",       // site UUID, required
  "seq": 42,               // sequence number (integer), optional
  "metrics": {             // key-value metric readings, required (at least one)
    "temp_c": 23.5,
    "humidity": 60
  },
  "provision_token": "...", // SHA256 device auth token, required
  "lat": 37.7749,           // latitude, optional
  "lng": -122.4194          // longitude, optional
}
```

For each field: type, required/optional, constraints, and what happens if missing/invalid.

**5. Rejection Taxonomy**
List every rejection reason code from `ingest_core.py` with:
- Code name (e.g., `UNKNOWN_DEVICE`)
- What causes it
- What the device should do in response

**6. Forward Compatibility Rules**
- Unknown fields are ignored (not rejected)
- The `version` field governs payload schema version
- Version `"1"` is the current version
- When version `"2"` is released, version `"1"` will be supported for N months (TBD)
- Devices SHOULD send `version: "1"` but are not required to (defaults to `"1"` if absent)

**7. Limits**
- Max payload size
- Max metrics per payload
- Rate limits (reference `services/shared/rate_limiter.py`)

**8. Example Payloads**
- Minimal valid payload (required fields only)
- Full payload (all fields)
- Invalid payload examples with expected rejection codes

## Acceptance Criteria

- [ ] File exists at `docs/specs/pulse-envelope-v1.md`
- [ ] All fields documented with types, constraints, and examples
- [ ] All rejection codes listed
- [ ] Forward compatibility rules written
- [ ] Document is accurate — cross-check every field against actual `validate_and_prepare()` in `services/shared/ingest_core.py`

## Important

Do not invent fields or behaviors. Read `services/shared/ingest_core.py` carefully and document only what actually exists. If you are unsure whether a field is validated, check the code.

# Prompt 004 — Add `version` Field to Pulse Envelope

## Context

The Pulse ingest envelope already exists and is well-implemented in `services/shared/ingest_core.py` via `validate_and_prepare()`. Both MQTT and HTTP ingest paths share it. The current payload structure is:

```json
{
  "ts": 1700000000,
  "site_id": "site-uuid",
  "seq": 42,
  "metrics": { "temp_c": 23.5, "humidity": 60 },
  "provision_token": "sha256-hash",
  "lat": 37.7749,
  "lng": -122.4194
}
```

This is **Pulse Envelope v1**. The problem: there is no `version` field, so we cannot evolve the envelope later without breaking existing devices. We need to add a `version` field NOW, before any devices are in production, so we can enforce forward compatibility.

## Your Task

**Read the following files first:**
- `services/shared/ingest_core.py` — find `validate_and_prepare()`, understand all fields validated
- `services/ingest_iot/main.py` — find where MQTT payloads are parsed and passed to `validate_and_prepare()`
- `services/ui_iot/routes/ingest.py` — find where HTTP payloads are parsed
- `services/device_simulator/` or `services/provision_api/` — find where test payloads are generated (so you can update them)

**Then make the following changes:**

### 1. Add `version` field to `validate_and_prepare()`

- Add `version` as an **optional** field with a default of `"1"` (string, not integer — easier to evolve: "1", "1.1", "2")
- Accept `"1"` as valid. Reject any other version with a clear error message: `UNSUPPORTED_ENVELOPE_VERSION`
- If `version` is absent, treat it as `"1"` (backwards compatible for existing devices)
- Store the version in `quarantine_events` when rejection occurs

### 2. Update the device simulator to send `version: "1"`

Find the device simulator and update its payload generation to include `"version": "1"`.

### 3. Do NOT change any other validation logic

This is an additive change only. Do not touch threshold logic, metric validation, auth, or anything else.

## Acceptance Criteria

- [ ] `validate_and_prepare()` accepts payloads with `version: "1"` or no version field
- [ ] `validate_and_prepare()` rejects payloads with `version: "2"` (or any unknown version) with reason `UNSUPPORTED_ENVELOPE_VERSION`
- [ ] Device simulator sends `version: "1"` in all payloads
- [ ] `pytest -m unit -v` passes with no regressions
- [ ] Add unit tests: valid v1 payload, missing version (defaults to v1), unknown version rejection

## Pattern Reference

Follow the existing validation pattern in `validate_and_prepare()`. Rejection reasons are string constants in `ingest_core.py`. Add `UNSUPPORTED_ENVELOPE_VERSION` to the existing set.

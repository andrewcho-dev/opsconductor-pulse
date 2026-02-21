# Prompt 003 — Audit and Harden Subscription Enforcement on All Ingest Paths

## Context

`check_device_access()` exists in `services/ui_iot/routes/ingest.py` and is meant to reject telemetry from devices whose tenant subscription is SUSPENDED or whose device limit has been exceeded. However, the codebase audit found that subscription status checks may not be called on ALL ingest code paths. This means a suspended tenant's devices may still successfully write telemetry depending on which path the message takes.

There are two ingest paths:
1. **MQTT path**: `services/ingest_iot/main.py` → `services/shared/ingest_core.py`
2. **HTTP path**: `services/ui_iot/routes/ingest.py` → `services/shared/ingest_core.py`

## Your Task

**Read the following files first:**
- `services/ui_iot/routes/ingest.py` — find `check_device_access()` and all call sites
- `services/ingest_iot/main.py` — find subscription check calls (or absence of them)
- `services/shared/ingest_core.py` — find `validate_and_prepare()` and `DeviceAuthCache`
- Any subscription-related tables/queries referenced in the above files

**Audit questions to answer in code comments:**
1. Does the MQTT ingest path call `check_device_access()` or equivalent before writing telemetry?
2. Does the HTTP ingest path call it on ALL endpoints (not just the primary one)?
3. Does `DeviceAuthCache` cache subscription status, or only device identity?
4. If a subscription transitions from ACTIVE → SUSPENDED mid-flight, how long until ingest rejects the device? (cache TTL)

**Then fix any gaps found:**

- If the MQTT path does not check subscription status, add the check before `TimescaleBatchWriter` writes
- If the HTTP path has endpoints that skip the check, add it to all of them
- If `DeviceAuthCache` does not cache subscription status, add it (cache the `subscription.status` alongside device auth data, with the same or shorter TTL)
- If the cache TTL allows a suspended tenant to continue writing for too long, reduce the TTL or add a bypass for SUSPENDED status

## Acceptance Criteria

- [ ] Both MQTT and HTTP ingest paths check subscription status before writing telemetry
- [ ] A device from a SUSPENDED subscription receives a rejection (not a silent drop)
- [ ] Rejection is logged with a quarantine reason (use existing `quarantine_events` table pattern)
- [ ] `pytest -m unit -v` passes with no regressions
- [ ] Add at least 2 unit tests: one for SUSPENDED subscription rejection on MQTT path, one on HTTP path

## Pattern Reference

Rejection taxonomy is in `services/shared/ingest_core.py`. Use existing rejection reason codes or add a new one: `SUBSCRIPTION_SUSPENDED`. Quarantine events follow the existing pattern in `quarantine_events` table.

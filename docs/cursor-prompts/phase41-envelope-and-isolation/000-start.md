# Phase 41: Pulse Envelope v1 + Tenant Isolation Hardening

## Why This Phase Comes First

Phase 40 (testing) is complete. Before any feature work (device twin, rules DSL, fleet UX, IaC), we must:

1. **Fix active tenant isolation bugs** — three correctness/security gaps found in the codebase audit
2. **Lock the ingest envelope contract** — the envelope already exists but is unversioned and undocumented

These are the foundation everything else depends on. Skipping them means building on an unsound base.

---

## Background: What the Audit Found

### Tenant Isolation Bugs (fix immediately)

**Bug 1 — `app.role` PostgreSQL setting never set**
- `telemetry` hypertable has an RLS policy `operator_read` that checks `current_setting('app.role')`
- `db/pool.py` never calls `set_config('app.role', ...)` before queries
- The policy is dead code. Operator bypass relies entirely on `BYPASSRLS` privilege on `pulse_operator` user (which works), but the second policy is misleading and fragile
- Fix: either set `app.role` correctly in the pool/connection context, or drop the dead policy

**Bug 2 — Ingest service connects with full DB access**
- `ingest_iot` service connects as the `iot` user which has both `pulse_app` and `pulse_operator` roles
- `SET LOCAL ROLE` is never called in the ingest path
- The ingest worker effectively bypasses RLS
- Mitigated by device auth cache + subscription checks + topic-based tenant validation, but a compromised ingest service could write to any tenant's data
- Fix: `SET LOCAL ROLE pulse_app` at the start of each ingest DB transaction

**Bug 3 — Subscription enforcement gaps on ingest path**
- `check_device_access()` exists in `services/ui_iot/routes/ingest.py` but subscription status checks may not be called on all code paths
- If a device's subscription is SUSPENDED, telemetry may still be accepted depending on code path
- Fix: audit all ingest code paths (MQTT + HTTP) and ensure subscription status check is called before writing telemetry

### Envelope Contract (version and document)

The Pulse ingest envelope already exists in `services/shared/ingest_core.py` via `validate_and_prepare()`. Both MQTT and HTTP ingest paths share it. What is missing:
- No `version` field on payloads
- No written spec / contract document
- No forward-compatibility rules
- No rejection reason for unknown/future versions

The fix is documentation + a `version` field addition. It is NOT a redesign.

---

## Execution Order

Execute prompts **in numerical order**. Each prompt is self-contained.

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Fix `app.role` dead RLS policy | CRITICAL |
| 002 | Fix ingest RLS bypass — SET LOCAL ROLE | CRITICAL |
| 003 | Audit and harden subscription enforcement on all ingest paths | CRITICAL |
| 004 | Add `version` field to envelope + update `validate_and_prepare()` | HIGH |
| 005 | Write Pulse Envelope v1 spec document | HIGH |
| 006 | Add unit tests for all three isolation fixes + envelope version handling | HIGH |

---

## Verification After All Prompts Complete

```bash
# Run unit tests
pytest -m unit -v

# Confirm no RLS bypass in ingest
grep -rn "SET LOCAL ROLE" services/ingest_iot/
grep -rn "app.role" services/

# Confirm envelope version field present
grep -rn '"version"' services/shared/ingest_core.py

# Confirm spec document exists
ls docs/specs/pulse-envelope-v1.md
```

---

## Key Files

- `services/shared/ingest_core.py` — `validate_and_prepare()`, `DeviceAuthCache`, `TimescaleBatchWriter`
- `services/ingest_iot/main.py` — MQTT ingest path
- `services/ui_iot/routes/ingest.py` — HTTP ingest path
- `db/pool.py` — DB connection pool (where `app.role` must be set)
- `db/migrations/` — RLS policy definitions
- `tests/unit/` — unit tests follow FakeConn/FakePool/monkeypatch/AsyncMock pattern

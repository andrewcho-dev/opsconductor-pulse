# Phase 108 — IoT Jobs

## Goal

Implement a durable, tracked command system modelled on AWS IoT Jobs.

An operator creates a Job with a document (`type` + `params`) and a target
(single device, device group, or all devices in the tenant). The platform
creates one `job_execution` record per targeted device. Each execution
progresses through a lifecycle independently:

```
QUEUED → IN_PROGRESS → SUCCEEDED
                     → FAILED
                     → TIMED_OUT
                     → REJECTED
```

Devices poll for pending jobs, claim them, execute, and report the outcome.
Operators monitor job progress per-job and per-device from the UI.

## Key design decisions (from architecture discussion)

- **Snapshot targeting**: group membership is resolved at job creation time,
  not at delivery time. If a device joins a group after the job is created,
  it does not receive that job.
- **Job document**: `{ "type": "reboot" | "update_config" | ..., "params": {...} }`
  — `type` is required and validated as non-empty string; `params` is freeform JSONB.
- **Targets**: single `device_id`, a `group_id`, or `"*"` (all devices in tenant).
- **TTL/expiry**: jobs have a configurable `expires_at`. The jobs worker marks
  `QUEUED` executions as `TIMED_OUT` when the job expires.
- **Device transport**: HTTP polling only for Phase 108. MQTT job notifications
  are an optimization for a later phase.
- **Device API lives in `ingest_iot`** (same as twin API, same auth model).

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-schema.md` | Migration 077: jobs + job_executions tables |
| `002-operator-api.md` | Job CRUD + execution monitoring in ui_iot |
| `003-device-api.md` | Device job poll + update endpoints in ingest_iot |
| `004-jobs-worker.md` | TTL expiry worker tick in ops_worker |
| `005-frontend.md` | Jobs page + execution status table |
| `006-verify.md` | Full lifecycle test, both targets, TTL expiry, commit |

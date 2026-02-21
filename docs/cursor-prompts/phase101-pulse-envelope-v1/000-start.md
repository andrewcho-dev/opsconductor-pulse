# Phase 101 — Pulse Envelope v1

## Goal
Formally version the ingest payload envelope. The envelope already exists implicitly in
`services/shared/ingest_core.py` — this phase documents it, adds a `version` field, and
freezes forward-compatibility rules so future envelope changes don't break existing devices.

## Files to execute in order
| File | What it does |
|------|-------------|
| `001-schema.md` | Migration 073: add version to quarantine_events; update ingest_core validation |
| `002-spec.md` | Write docs/PULSE_ENVELOPE_V1.md — the canonical envelope specification |
| `003-verify.md` | Verify version field accepted + spec committed |

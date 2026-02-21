# Phase 104 — Time-Window Alert Rules

## Goal

Alert rules currently fire on a single telemetry sample that exceeds a
threshold. This produces alert storms when a metric briefly spikes.

Add a **duration window**: "fire only if metric exceeds threshold continuously
for N minutes". This is the most-requested feature from operators.

## Design

- `alert_rules` gains `duration_minutes` (integer, nullable, default NULL).
- `NULL` means instant fire (current behavior, unchanged).
- `> 0` means: the condition must be true for every sample in the last
  `duration_minutes` minutes. If any sample in that window was below the
  threshold, the rule does not fire.
- No new tables required — the evaluator queries `telemetry` directly for the
  window check.

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-migration.md` | Migration 074: add duration_minutes to alert_rules |
| `002-evaluator.md` | Update evaluator to enforce time-window check |
| `003-api.md` | Accept duration_minutes in alert rule CRUD endpoints |
| `004-frontend.md` | Duration field in Create/Edit Alert Rule modal |
| `005-verify.md` | E2E test, commit |
